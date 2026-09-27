"""R54 抽查脚本（spotcheck-config.py）的负向自测。

纪律（skill 坑 46/66/75/82/93/104）：
  * 每个判定分支都有反例；每条注入断言「恰好新增目标断言」（按**断言前缀**比对，不拿整行当键）；
  * 注入必须**真的改到源码**（mutate 返回未命中锚点列表，先断言为空再跑判别力用例）；
  * 空夹具必须变红（防空转假绿）；合规夹具必须 rc=0 且 FAIL 0；
  * 真实仓库只读守卫 + 夹具零写副作用。
脚本与夹具**分目录**（坑 106）：脚本在 aap-r54-spotcheck/，夹具在 aap-r54-spotcheck-fixtures/。
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = HERE / "spotcheck-config.py"
TMP = Path(os.environ.get("LOCALAPPDATA", "C:/Users/laitz/AppData/Local")) / "Temp"
FIXT = TMP / "aap-r54-spotcheck-fixtures"
OK = FIXT / "ok"
ENV = FIXT / "ok.env"
WORK = TMP / "aap-r54-spotcheck-work"
REAL = Path("E:/workspaces/hioas/hioas-aap-001")

FAIL_RX = re.compile(r"^\[FAIL\]\s+(\S+)", re.M)
RESULTS: list[str] = []
MISSES: list[str] = []


def check(cond: bool, msg: str) -> None:
    RESULTS.append(("[PASS] " if cond else "[FAIL] ") + msg)


def run(root: Path, env: Path | None = None):
    p = subprocess.run(
        [sys.executable, str(AUDIT), "--root", str(root), "--env-file", str(env or ENV)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def fails(out: str) -> set[str]:
    return set(FAIL_RX.findall(out))


def mutate(path: Path, old: str, new: str, count: int = -1) -> bool:
    txt = path.read_text(encoding="utf-8")
    if old not in txt:
        MISSES.append(f"{path.name}: 锚点未命中 -> {old[:60]!r}")
        return False
    path.write_text(txt.replace(old, new) if count < 0 else txt.replace(old, new, count), encoding="utf-8")
    return True


def md5tree(root: Path) -> dict[str, str]:
    out = {}
    for f in sorted(root.rglob("*")):
        if f.is_file():
            out[f.relative_to(root).as_posix()] = hashlib.md5(f.read_bytes()).hexdigest()
    return out


def fresh(name: str) -> Path:
    dst = WORK / name
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(OK, dst)
    return dst


def case(name: str, expect: set[str], muts: list[tuple[Path, str, str]], extra_check=None) -> None:
    root = fresh(name)
    for path, old, new in muts:
        mutate(root / path, old, new)
    before = md5tree(root)
    rc, out = run(root)
    after = md5tree(root)
    got = fails(out)
    check(got == expect, f"{name}：rc={rc} FAIL 集合={sorted(got)} 期望={sorted(expect)}")
    check(before == after, f"{name}：夹具未被改写（零写副作用）")
    if extra_check:
        extra_check(out)


# ---------------------------------------------------------------- 前置
if not AUDIT.exists() or not OK.exists():
    print(f"[FAIL] 前置缺失：audit={AUDIT.exists()} fixture={OK.exists()}")
    sys.exit(1)
if WORK.exists():
    shutil.rmtree(WORK)

# 1) 合规夹具
rc_ok, out_ok = run(OK)
ok_fails = fails(out_ok)
summary_ok = re.search(r"断言 \d+ 条：PASS \d+，FAIL 0", out_ok)
check(rc_ok == 0 and not ok_fails, f"合规夹具：rc={rc_ok} 且 FAIL 0（正向对照：汇总行 {bool(summary_ok)}）")
check(bool(summary_ok), "合规夹具：断言汇总行显示 FAIL 0（解析器真的工作了）")

# 2) 空夹具必须变红
empty = fresh("empty")
(empty / "aap-server/src/main/resources/application.yml").write_text("", encoding="utf-8")
(empty / "aap-server/src/test/resources/application-test.yml").write_text("", encoding="utf-8")
shutil.rmtree(empty / "aap-server/src/main/java")
rc_e, out_e = run(empty)
fe = fails(out_e)
check({"A0a", "A0b", "A0c"} <= fe, f"空夹具：A0a/A0b/A0c 必须点名 FAIL（防空转假绿）→ 实际 {sorted(fe)}")

# 3) 注入缺陷（每条恰好新增目标断言）
case("inj_a1b_undeclared_reader", {"A1b"},
     [("aap-server/src/main/java/com/hioas/aap/config/ConfigReaders.java",
       '    @Value("${app.detection.recheck-interval-days:30}")',
       '    @Value("${app.foo.timeout:7}")\n    private int fooTimeout;\n\n    @Value("${app.detection.recheck-interval-days:30}")')])

case("inj_a1_no_default", {"A1"},
     [("aap-server/src/main/java/com/hioas/aap/config/ConfigReaders.java",
       '    @Value("${app.usage.log-file:}")',
       '    @Value("${app.bar.baz}")\n    private String baz;\n\n    @Value("${app.usage.log-file:}")')])

case("inj_a2_orphan_key", {"A2"},
     [("aap-server/src/main/resources/application.yml",
       "  usage:\n    log-file:",
       "  orphan:\n    nobody-reads-me: 1\n  usage:\n    log-file:")])

case("inj_a3a_main_expose_true", {"A3a"},
     [("aap-server/src/main/resources/application.yml",
       "expose-code: ${AAP_SMS_EXPOSE_CODE:false}",
       "expose-code: ${AAP_SMS_EXPOSE_CODE:true}")])

case("inj_a3d_test_not_relaxed", {"A3d"},
     [("aap-server/src/test/resources/application-test.yml", "expose-code: true", "expose-code: false")])

case("inj_a4_default_drift", {"A4"},
     [("aap-server/src/main/java/com/hioas/aap/config/ConfigReaders.java",
       '@Value("${app.detection.pass-score:70}")', '@Value("${app.detection.pass-score:60}")')])

case("inj_a5_hardcoded_dup", {"A5"},
     [("aap-server/src/main/java/com/hioas/aap/config/ConfigReaders.java",
       "public class ConfigReaders {",
       "public class ConfigReaders {\n\n    static String tone(int score) {\n        return score >= 70 ? \"success\" : \"danger\";\n    }\n")])

case("inj_a6_port_drift", {"A6"},
     [("aap-client/src/api/base-url.ts", "127.0.0.1:8084", "127.0.0.1:9999")])

case("inj_a7_secret_literal", {"A7"},
     [("aap-server/src/main/resources/application.yml", "secret: ${AAP_JWT_SECRET}", "secret: fixture-plain-secret")])

case("inj_a10a_positive_control", {"A10a"},
     [("aap-server/src/main/java/com/hioas/aap/adminconfig/DetectionConfigService.java",
       "from aap_detection_config order by version_no", "from fixture_config order by version_no")])


# 4) INFO 分支也要有判别力（A9 绑定组零读取：不判 FAIL，但必须能被注入触发）
def a9_check(out: str) -> None:
    check("A9 绑定组 app.detection.* 在实现里零读取" in out, "inj_a9 绑定组零读取：INFO 行点名 app.detection.*（INFO 分支判别力）")


case("inj_a9_binding_group_unused", set(),
     [("aap-server/src/main/java/com/hioas/aap/config/ConfigReaders.java",
       "properties.detection().passScore() + ", "")], extra_check=a9_check)

# 5) 注入锚点必须全部命中（否则「注入没改到源码」→ 空转通过，坑 66/94）
check(not MISSES, f"注入锚点全部命中（未命中 {len(MISSES)} 条）" + ("" if not MISSES else "：" + "；".join(MISSES)))

# 6) 真实仓库只读守卫
REAL_FILES = [
    REAL / "aap-server/src/main/resources/application.yml",
    REAL / "aap-server/src/test/resources/application-test.yml",
    REAL / "aap-server/src/main/java/com/hioas/aap/config/AppProperties.java",
    REAL / "docs/backend/00-设计总览.md",
]
before_real = {f: hashlib.md5(f.read_bytes()).hexdigest() for f in REAL_FILES}
rc_r, out_r = run(REAL, Path("E:/env/aap-server.env"))
after_real = {f: hashlib.md5(f.read_bytes()).hexdigest() for f in REAL_FILES}
check(before_real == after_real, "真实仓库跑一遍：4 个关键文件 md5 全等（只读守卫）")
check(rc_r == 1 and bool(fails(out_r)), f"真实仓库：rc={rc_r} 且报出 FAIL {sorted(fails(out_r))}（存在待拍板/漂移，符合预期）")

print("\n".join(RESULTS))
print()
nf = sum(1 for r in RESULTS if r.startswith("[FAIL]"))
print(f"自测断言 {len(RESULTS)} 条：PASS {len(RESULTS) - nf}，FAIL {nf}")
print("结论：" + ("全部通过" if nf == 0 else "存在失败项"))
sys.exit(1 if nf else 0)
