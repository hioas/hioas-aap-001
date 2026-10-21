"""loop.py 第 4 条（watch 范围反作弊）自测。

两个分支：
  A) watch 路径**有未提交改动** → 应判 DONE
  B) watch 路径干净、但**仓库别处**有改动（模拟并发仓库里他方在制品）→ 必须被判伪
     （修复前的旧实现会错误地判 DONE —— 这就是本次要证明的点）

用法：python loop_scope_selftest.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # tools/loop/x.py -> repo
LOOP = os.path.join(REPO, "tools", "loop", "loop.py")

root = tempfile.mkdtemp(prefix="loop-selftest-")


def run(cmd):
    return subprocess.run(cmd, cwd=root, shell=True, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


# 建一个独立 git 仓库：src/dirty 有改动；src/clean 干净；other/ 有改动（充当"他方在制品"）
os.makedirs(os.path.join(root, "src", "dirty"), exist_ok=True)
os.makedirs(os.path.join(root, "src", "clean"), exist_ok=True)
os.makedirs(os.path.join(root, "other"), exist_ok=True)
for rel, text in [("src/dirty/a.txt", "v1"), ("src/clean/b.txt", "v1"), ("other/c.txt", "v1")]:
    with open(os.path.join(root, rel), "w", encoding="utf-8") as f:
        f.write(text)
run("git init -q && git add -A && git -c user.email=t@t -c user.name=t commit -qm base")
# 改动：dirty 路径 + 他处（other）
with open(os.path.join(root, "src", "dirty", "a.txt"), "w", encoding="utf-8") as f:
    f.write("v2")
with open(os.path.join(root, "other", "c.txt"), "w", encoding="utf-8") as f:
    f.write("v2")

tasks = {
    "feature": "selftest",
    "tasks": [
        {"id": "T-DIRTY", "title": "watch 内有改动", "green": "echo green-ok",
         "gate": [], "watch": ["src/dirty"], "max_attempts": 1},
        {"id": "T-CLEAN", "title": "watch 内干净（他处有改动）", "green": "echo green-ok",
         "gate": [], "watch": ["src/clean"], "max_attempts": 1},
    ],
}
with open(os.path.join(root, "tasks.json"), "w", encoding="utf-8") as f:
    json.dump(tasks, f, ensure_ascii=False, indent=2)

cases = []
for tid, expect_done, must_contain in [
        ("T-DIRTY", True, "四条件通过"),
        ("T-CLEAN", False, "watch 范围内无改动")]:
    p = subprocess.run([sys.executable, LOOP, "--repo", root, "--tasks", os.path.join(root, "tasks.json"),
                        "--task", tid, "--once"],
                       cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    done = ("-> DONE" in out)
    ok = (done == expect_done) and (must_contain in out)
    cases.append((tid, expect_done, done, ok, out.strip().splitlines()[-3:] if out.strip() else []))

print("=== 自测结果 ===")
allok = True
for tid, exp, got, ok, tail in cases:
    allok = allok and ok
    print(("  PASS  " if ok else "  FAIL  ") + f"{tid}: 期望 DONE={exp} 实际 DONE={got}")
    for line in tail:
        print("          " + line.strip()[:150])
print("\n结论：" + ("两分支均符合预期（watch 范围判定生效）" if allok else "存在不符合项"))

shutil.rmtree(root, ignore_errors=True)
sys.exit(0 if allok else 1)
