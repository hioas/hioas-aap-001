# -*- coding: utf-8 -*-
"""gen-backend-models.py --check 的**负向自测**：判定有几个分支，就配几条反例。

背景（真实返工）：`--check` 原先只比 openapi.yaml，而 gen_* / fix_model_refs /
emit_endpoint_manifest 在 check 模式下**仍无条件写仓库文件** →
（a）schema 与 endpoints.json 的漂移永远检不出来（被静默覆盖），
（b）标着「只校验」的命令实际改写了 82 个文件。
修好之后必须证明它有判别力，否则 rc=0 无法区分「真干净」与「比对逻辑全错」。

覆盖分支：
  A 正向：干净仓库 → rc=0，且 84 个产物的 (mtime_ns, size, md5) 一个都不变（零写副作用）
  B 语义漂移：改写某个 schema 的 title → rc=1 且 stderr 点名该文件；工具不得把它改写回去
  C1 产物缺失：把某个 schema 移走 → rc=1 且点名该文件
  C2 孤儿产物：多出一个生成器不产出的 schema → rc=1 且判为「孤儿」
  D 生成模式：python gen-backend-models.py → 84 个产物与基线逐字节一致

用法： python tools/gen-backend-models-selftest.py
退出码：0 = 全部断言通过（自测有判别力）；1 = 有断言失败
纪律：全程只动临时目录 + 自测自己注入的漂移，结束时把仓库恢复原状（失败也在 finally 里恢复）。
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(ROOT, "tools", "gen-backend-models.py")
SCHEMA_DIR = os.path.join(ROOT, "docs", "backend", "json-schema")
DOCS = os.path.join(ROOT, "docs", "backend")

RESULTS = []


def check(cond: bool, label: str, detail: str = "") -> bool:
    RESULTS.append((bool(cond), label, detail))
    print(("  [PASS] " if cond else "  [FAIL] ") + label + (("  (" + detail + ")") if detail else ""))
    return bool(cond)


def md5(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.md5(fh.read()).hexdigest()


def fingerprint(paths: list) -> dict:
    out = {}
    for p in paths:
        st = os.stat(p)
        out[p] = (st.st_mtime_ns, st.st_size, md5(p))
    return out


def artifact_paths() -> list:
    """与生成器一致的产物清单：common 3 + models/requests（由 --check 的输出核对数量）。"""
    paths = []
    for sub in ("common", "models", "requests"):
        d = os.path.join(SCHEMA_DIR, sub)
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".schema.json"):
                paths.append(os.path.join(d, fn))
    paths += [os.path.join(DOCS, "endpoints.json"), os.path.join(DOCS, "openapi.yaml")]
    return paths


def run_gen(extra: list) -> tuple:
    proc = subprocess.run([sys.executable, GEN] + extra, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    return proc.returncode, (proc.stdout or ""), (proc.stderr or "")


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="aap-gen-selftest-")
    paths = artifact_paths()
    backups = {}
    injected = os.path.join(SCHEMA_DIR, "models", "audit-log.schema.json")
    missing = os.path.join(SCHEMA_DIR, "models", "report-template.schema.json")
    orphan = os.path.join(SCHEMA_DIR, "models", "report-template-renamed.schema.json")
    try:
        print("---- 分支 A：正向（干净仓库）----")
        base = fingerprint(paths)
        rc, out, err = run_gen(["--check"])
        check(rc == 0, "干净仓库 --check → rc=0", "rc=%d" % rc)
        check("84/84" in out, "输出声明 84/84 个产物一致", out.strip().splitlines()[0] if out else "")
        after = fingerprint(paths)
        changed = [p for p in paths if base[p] != after[p]]
        check(not changed, "零写副作用：84 个产物 (mtime,size,md5) 全不变",
              "变化的文件数=%d %s" % (len(changed), [os.path.relpath(p, ROOT) for p in changed[:3]]))

        print("---- 分支 B：语义漂移（改 title）----")
        backups[injected] = injected + ".selftest-bak"
        shutil.copy2(injected, backups[injected])
        import json
        with open(injected, encoding="utf-8") as fh:
            obj = json.load(fh)
        obj["title"] = obj.get("title", "") + "-DRIFTED-BY-SELFTEST"
        with open(injected, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        drifted_md5 = md5(injected)
        rc, out, err = run_gen(["--check"])
        check(rc == 1, "漂移后 --check → rc=1", "rc=%d" % rc)
        check("audit-log.schema.json" in err, "stderr 点名漂移文件", err.strip().splitlines()[0] if err else "")
        check(md5(injected) == drifted_md5, "只读：工具未改写漂移文件（不是靠覆盖来「修好」）")
        shutil.copy2(backups[injected], injected)
        check(md5(injected) == base[injected][2], "自测已还原注入的漂移")

        print("---- 分支 C1：产物缺失 ----")
        shutil.move(missing, os.path.join(tmp, "report-template.bak"))
        rc, out, err = run_gen(["--check"])
        check(rc == 1, "产物缺失后 --check → rc=1", "rc=%d" % rc)
        check("report-template.schema.json" in err, "stderr 点名缺失产物", err.strip().splitlines()[0] if err else "")
        shutil.move(os.path.join(tmp, "report-template.bak"), missing)

        print("---- 分支 C2：孤儿产物（生成器已不产出）----")
        shutil.copy2(missing, orphan)
        rc, out, err = run_gen(["--check"])
        check(rc == 1, "出现孤儿产物后 --check → rc=1", "rc=%d" % rc)
        check("report-template-renamed.schema.json" in err and "孤儿" in err, "stderr 判为孤儿产物",
              err.strip().splitlines()[0] if err else "")
        os.remove(orphan)

        print("---- 分支 D：生成模式逐字节一致 ----")
        rc, out, err = run_gen([])
        check(rc == 0, "生成模式 → rc=0", "rc=%d" % rc)
        after = fingerprint(paths)
        diff = [p for p in paths if base[p][2] != after[p][2]]
        check(not diff, "生成产物与基线逐字节一致（内容 md5 不变，仅 mtime 变）",
              "内容变化的文件数=%d %s" % (len(diff), [os.path.relpath(p, ROOT) for p in diff[:3]]))

        print("---- 收尾：仓库必须干净（自测零残留）----")
        after = fingerprint(paths)
        left = [p for p in paths if base[p][2] != after[p][2]]
        check(not left, "所有产物内容回到基线（无残留）",
              "残留=%s" % [os.path.relpath(p, ROOT) for p in left[:3]])
    finally:
        for p, bak in backups.items():
            if os.path.exists(bak):
                shutil.copy2(bak, p)
                os.remove(bak)
        if os.path.exists(orphan):
            os.remove(orphan)
        if os.path.exists(os.path.join(tmp, "report-template.bak")):
            shutil.move(os.path.join(tmp, "report-template.bak"), missing)
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [label for ok, label, _ in RESULTS if not ok]
    print()
    if failed:
        print("结果：FAILED（%d/%d 条断言未通过）" % (len(failed), len(RESULTS)))
        for label in failed:
            print("  - " + label)
        return 1
    print("结果：全部通过（%d 条断言，自测有判别力）" % len(RESULTS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
