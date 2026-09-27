"""R54 抽查（第二十八类可审计不变量）：配置项契约一致性（只读）。

真源：
  Y = aap-server/src/main/resources/application.yml（主配置：键集合 + 占位默认值 + 安全默认）
  T = aap-server/src/test/resources/application-test.yml（测试覆盖：仅测试环境可放宽）
  J = 实现读取点（@Value / @ConfigurationProperties 绑定 / @ConditionalOnProperty / @Scheduled / Environment.getProperty）
  L = log4j2-spring.xml 的 ${spring:app.xxx} 查找
  D = docs/backend/00-设计总览.md §6.1 端口登记 + 02-API接口模型清单.md 声明的业务参数
  H = 与「有配置项的参数」同值的硬编码字面量（配置漂移风险点）
  E = E:/env/aap-server.env 的**变量名集合**（只比名字，绝不读取/回显值）

为什么两套门禁都看不见：契约测试只读 JSON Schema（配置不是响应体），覆盖门禁只比「方法+路径」，
openapi/客户端 TS 不被任何测试读取；配置项「声明 ⇔ 读取 ⇔ 默认值 ⇔ 安全默认」的漂移对 204 例全绿完全不可见。

用法：python spotcheck-config.py --root <仓库或夹具根> [--env-file <path>]
退出码：0 = 无 FAIL；1 = 有 FAIL（或源文件缺失）
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except Exception:  # pragma: no cover
    print("FATAL 缺少 PyYAML，无法解析 application.yml（显式失败，不静默跳过）")
    sys.exit(2)

FAILS: list[str] = []
PASSES: list[str] = []
INFOS: list[str] = []


def ok(aid: str, msg: str) -> None:
    PASSES.append(f"[PASS] {aid} {msg}")


def bad(aid: str, msg: str) -> None:
    FAILS.append(f"[FAIL] {aid} {msg}")


def info(msg: str) -> None:
    INFOS.append(f"[INFO] {msg}")


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


# ---------------------------------------------------------------- 解析
def flatten(node, prefix="") -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(node, dict):
        for k, v in node.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            out.update(flatten(v, key))
    elif isinstance(node, list):
        pass  # 列表不参与键集合断言
    elif isinstance(node, bool):
        out[prefix] = "true" if node else "false"
    else:
        out[prefix] = "" if node is None else str(node)
    return out


def load_yml(path: Path) -> dict[str, str]:
    return flatten(yaml.safe_load(read(path)))


PLACEHOLDER = re.compile(r"\$\{([A-Za-z0-9_.\-]+)(?::([^}]*))?\}")


def placeholder_of(value: str):
    """返回 (var, default) 或 None（非占位）。"""
    m = PLACEHOLDER.fullmatch(value.strip())
    if not m:
        return None
    return m.group(1), m.group(2)


def kebab(name: str) -> str:
    return re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", name).lower()


JAVA_VALUE = re.compile(r'Value\(\s*"\$\{([A-Za-z0-9_.\-]+)(?::([^}]*))?\}"\s*\)')
JAVA_COND = re.compile(r'ConditionalOnProperty\(\s*name\s*=\s*"([A-Za-z0-9_.\-]+)"')
JAVA_SCHED = re.compile(r'Scheduled\([^)]*"\$\{([A-Za-z0-9_.\-]+)(?::([^}]*))?\}"')
JAVA_ENVPROP = re.compile(r'getProperty\(\s*"([A-Za-z0-9_.\-]+)"\s*(?:,\s*"([^"]*)")?')


def java_readers(root: Path):
    """返回 [(key, default|None, file, line)]"""
    out = []
    base = root / "aap-server/src/main/java"
    for f in sorted(base.rglob("*.java")):
        for i, ln in enumerate(read(f).split("\n"), 1):
            for rx in (JAVA_VALUE, JAVA_SCHED):
                for m in rx.finditer(ln):
                    out.append((m.group(1), m.group(2), f, i))
            for m in JAVA_COND.finditer(ln):
                out.append((m.group(1), None, f, i))
            for m in JAVA_ENVPROP.finditer(ln):
                out.append((m.group(1), m.group(2), f, i))
    return out


RECORD_RX = re.compile(r"record\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)")
FIELD_RX = re.compile(r"\b(?:int|long|boolean|String|Duration)\s+([a-zA-Z0-9_]+)")


def config_properties_bindings(root: Path):
    """解析 @ConfigurationProperties(prefix="app") 的嵌套 record → [(key, file, line)]"""
    out = []
    base = root / "aap-server/src/main/java"
    for f in sorted(base.rglob("*.java")):
        txt = read(f)
        if "@ConfigurationProperties" not in txt:
            continue
        prefix_m = re.search(r'@ConfigurationProperties\(\s*prefix\s*=\s*"([^"]+)"', txt)
        if not prefix_m:
            continue
        prefix = prefix_m.group(1)
        top = RECORD_RX.search(txt)  # 顶层 record（字段为各组）
        if not top:
            continue
        groups = []
        for comp in top.group(2).split(","):
            comp = comp.strip()
            if not comp:
                continue
            ids = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", comp)
            if ids:
                groups.append(ids[-1])
        for g in groups:
            # 找同名嵌套 record
            for m in RECORD_RX.finditer(txt):
                if m.group(1) == g[0].upper() + g[1:]:
                    for fld in FIELD_RX.findall(m.group(2)):
                        out.append((f"{prefix}.{kebab(g)}.{kebab(fld)}", f, txt[: m.start()].count("\n") + 1))
    return out


LOG4J_LOOKUP = re.compile(r"\$\{spring:([A-Za-z0-9_.\-]+)(?::-([^}]*))?\}")


def log4j_lookups(root: Path):
    p = root / "aap-server/src/main/resources/log4j2-spring.xml"
    if not p.exists():
        return []
    return [(m.group(1), m.group(2), p, 1) for m in LOG4J_LOOKUP.finditer(read(p))]


# 业务参数表：(参数名, 配置键, 代码关键词正则, 文档声明正则, 扫描范围（实现子路径，None=全量）)
# 范围按语义收窄（坑 81：判据范围必须与断言语义一致）——sms.* 只可能被认证/短信模块消费，
# 否则同名同值但语义不同的常量（如同步重试上限 5）会被误报成「配置副本」。
PARAMS = [
    ("通过线", "app.detection.pass-score", r"(?i)score", r"通过线\s*(\d+)", None),
    ("否决线", "app.detection.veto-score", r"(?i)score|veto", r"否决线\s*(\d+)", None),
    ("日配额", "app.detection.daily-quota", r"(?i)quota", r"日配额\s*(\d+)\s*次", None),
    ("复测间隔(天)", "app.detection.recheck-interval-days", r"(?i)recheck|intervalDays", r"报告有效期\s*(\d+)\s*天", None),
    ("验证码重发间隔(秒)", "app.sms.resend-interval-seconds", r"(?i)resend", r"重发间隔\s*(\d+)", "/iam/"),
    ("验证码有效期(秒)", "app.sms.ttl-seconds", r"(?i)ttl", r"验证码有效期\s*(\d+)", "/iam/"),
    ("验证码尝试上限", "app.sms.max-attempts", r"(?i)attempt", r"尝试上限\s*(\d+)", "/iam/"),
    ("锁定分钟", "app.sms.lock-minutes", r"(?i)lock", r"锁定\s*(\d+)\s*分钟", "/iam/"),
]


def hardcoded_hits(root: Path, key: str, value: str, kw: str, reader_lines, scope=None):
    """在实现里找「与配置项同值、且行内含该参数关键词」的字面量（排除配置读取点自身与注释）。"""
    code, comment = [], []
    base = root / "aap-server/src/main/java"
    val_rx = re.compile(rf"(?<![0-9.]){re.escape(value)}(?![0-9.])")
    kw_rx = re.compile(kw)
    for f in sorted(base.rglob("*.java")):
        rel = f.relative_to(root).as_posix()
        if scope and scope not in "/" + rel:
            continue
        lines = read(f).split("\n")
        for i, ln in enumerate(lines, 1):
            if (f, i) in reader_lines or "${" + key in ln:
                continue
            if not val_rx.search(ln) or not kw_rx.search(ln):
                continue
            stripped = ln.strip()
            (comment if stripped.startswith("*") or stripped.startswith("//") or stripped.startswith("/*") else code).append(
                f"{rel}:{i} {stripped[:110]}"
            )
    return code, comment


# ---------------------------------------------------------------- 主流程
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="E:/workspaces/hioas/hioas-aap-001")
    ap.add_argument("--env-file", default="E:/env/aap-server.env")
    args = ap.parse_args()
    root = Path(args.root)
    print(f"根目录：{root.as_posix()}（仓库外路径也照常显示）")
    print("== 配置项契约一致性抽查（第二十八类可审计不变量） ==")

    yml_p = root / "aap-server/src/main/resources/application.yml"
    test_p = root / "aap-server/src/test/resources/application-test.yml"
    for p in (yml_p, test_p):
        if not p.exists():
            bad("A0z", f"源文件缺失：{p}")
            print("\n".join(FAILS))
            return 1

    Y = load_yml(yml_p)
    T = load_yml(test_p)
    readers = java_readers(root)
    bindings = config_properties_bindings(root)
    lookups = log4j_lookups(root)

    # 绑定组的「是否被读取」：properties.<group>() 在其它文件的引用
    all_java = "\n".join(read(f) for f in (root / "aap-server/src/main/java").rglob("*.java"))
    bound_groups = sorted({k.split(".")[1] for k, _, _ in bindings if k.count(".") >= 2})
    lookup_groups = {k.split(".")[1] for k, _, _, _ in lookups if k.startswith("app.") and k.count(".") >= 2}
    for g in bound_groups:
        if g in lookup_groups:
            ok("A9", f"绑定组 app.{g}.* 由 log4j2 查找（`${{spring:app.{g}.…}}`）消费，非零读取")
            continue
        n = len(re.findall(rf"properties\.{g}\(\)|\.{g}\(\)\.", all_java))
        if n == 0:
            info(f"A9 绑定组 app.{g}.* 在实现里零读取（绑定声明与读取点不一致；字段：{', '.join(k.split('.')[-1] for k, _, _ in bindings if k.split('.')[1] == g)}）")
        else:
            ok("A9", f"绑定组 app.{g}.* 有 {n} 处读取点")

    ykeys = {k: v for k, v in Y.items() if k.startswith("app.")}
    tkeys = {k: v for k, v in T.items() if k.startswith("app.")}
    all_readers = readers + lookups

    # ---- 正向对照 ----
    ok("A0a", f"Y 解析到 app.* 键 = {len(ykeys)}") if ykeys else bad("A0a", "Y 解析到 app.* 键 = 0（解析器失效）")
    ok("A0b", f"T 解析到 app.* 键 = {len(tkeys)}") if tkeys else bad("A0b", "T 解析到 app.* 键 = 0（解析器失效）")
    ok("A0c", f"J 解析到配置读取点 = {len(readers)} + L log4j2 查找 = {len(lookups)} + 绑定键 = {len(bindings)}") if (
        readers and lookups and bindings
    ) else bad("A0c", f"读取点/查找/绑定解析不足：readers={len(readers)} lookups={len(lookups)} bindings={len(bindings)}")
    ok("A0d", f"硬编码字面量扫描已启用（参数表 {len(PARAMS)} 条）")

    # ---- A1 读取点键声明/默认值 ----
    declared = set(ykeys) | set(tkeys)
    reader_lines = {(f, i) for _, _, f, i in all_readers}
    undeclared_default, undeclared_nodefault = [], []
    for key, default, f, i in readers + lookups:
        if key in declared:
            continue
        rel = f.relative_to(root).as_posix()
        (undeclared_default if default is not None else undeclared_nodefault).append(f"{key} ({rel}:{i}，内联默认 {default!r})")
    for key, f, i in bindings:
        if key not in declared:
            undeclared_nodefault.append(f"{key} ({f.relative_to(root).as_posix()}:{i}，@ConfigurationProperties 绑定)")
    if undeclared_nodefault:
        bad("A1", f"读取点引用的键既未声明也无默认值（启动即失败风险）= {len(undeclared_nodefault)} 条：" + "；".join(undeclared_nodefault))
    else:
        ok("A1", "所有读取点引用的键都在主/测试配置里声明或有内联默认值")
    if undeclared_default:
        bad("A1b", f"读取点键未在任一 yml 声明、仅靠内联默认 = {len(undeclared_default)} 条（运维在 yml 里找不到锚点，与其它键处理不一致）：" + "；".join(undeclared_default))
    else:
        ok("A1b", "所有读取点键都在 yml 里有显式声明（0 条仅靠内联默认）")

    # ---- A2 孤儿键（声明但零读取） ----
    read_keys = {k for k, _, _, _ in all_readers} | {k for k, _, _ in bindings}
    orphans = sorted(k for k in (set(ykeys) | set(tkeys)) if k not in read_keys)
    if orphans:
        bad("A2", f"孤儿配置键（yml 声明但实现零读取）= {len(orphans)} 条：" + "；".join(orphans))
    else:
        ok("A2", f"Y+T 的 {len(set(ykeys) | set(tkeys))} 个 app.* 键全部有读取点（孤儿 0）")

    # ---- A3 安全默认 / 测试专用开关 ----
    def placeholder_default(d: dict, key: str):
        v = d.get(key)
        if v is None:
            return None, None
        ph = placeholder_of(v)
        return (ph[1] if ph else v), ph

    exp, _ = placeholder_default(Y, "app.sms.expose-code")
    if exp == "false":
        ok("A3a", "主配置 app.sms.expose-code 默认 false（生产红线：不回显验证码）")
    else:
        bad("A3a", f"主配置 app.sms.expose-code 默认值不是 false：{exp!r}")
    lb, _ = placeholder_default(Y, "app.credential.allow-loopback")
    if lb == "false":
        ok("A3b", "主配置 app.credential.allow-loopback 默认 false（SSRF 防护默认不放行环回）")
    else:
        bad("A3b", f"主配置 app.credential.allow-loopback 默认值不是 false：{lb!r}")
    if "spring.flyway.clean-disabled" in Y:
        bad("A3c", "测试专用开关 spring.flyway.clean-disabled 出现在**主**配置（危险）")
    else:
        ok("A3c", "测试专用开关 spring.flyway.clean-disabled 不在主配置")
    texp, _ = placeholder_default(T, "app.sms.expose-code")
    tlb, _ = placeholder_default(T, "app.credential.allow-loopback")
    if texp == "true" and tlb == "true" and "spring.flyway.clean-disabled" in T:
        ok("A3d", "测试配置里 expose-code/allow-loopback/clean-disabled 均按要求放宽（正向对照）")
    else:
        bad("A3d", f"测试配置未按预期放宽：expose-code={texp!r} allow-loopback={tlb!r} clean-disabled={'spring.flyway.clean-disabled' in T}")

    # ---- A4 数值参数跨源一致 ----
    md00 = root / "docs/backend/00-设计总览.md"
    md02 = root / "docs/backend/02-API接口模型清单.md"
    mdtext = (read(md00) if md00.exists() else "") + "\n" + (read(md02) if md02.exists() else "")
    reader_defaults = {}
    for key, default, _, _ in all_readers:
        if default is not None:
            reader_defaults.setdefault(key, default)
    hard_findings = []
    for name, key, kw, md_rx, scope in PARAMS:
        yv = Y.get(key)
        if yv is None:
            info(f"A4 {name}（{key}）主配置未声明 → 跳过取值比对")
            continue
        srcs = [("Y", yv)]
        if key in reader_defaults:
            srcs.append(("@Value 默认", reader_defaults[key]))
        mdm = re.search(md_rx, mdtext)
        if mdm:
            srcs.append(("md 声明", mdm.group(1)))
        vals = {v for _, v in srcs}
        code, comment = hardcoded_hits(root, key, yv, kw, reader_lines, scope)
        if len(vals) > 1:
            bad("A4", f"{name}（{key}）跨源取值不一致：" + "、".join(f"{s}={v}" for s, v in srcs))
        else:
            ok("A4", f"{name}（{key}）= {yv} 在 " + "、".join(s for s, _ in srcs) + " 一致")
        if code:
            hard_findings.append((name, key, yv, code))
            info(f"A5 {name}（{key}）另有 {len(code)} 处同值硬编码（配置漂移风险点）：" + "；".join(code[:4]))
        if comment:
            info(f"A5b {name}（{key}）注释/javadoc 中提到同值 {len(comment)} 处（文档性，不计漂移）")
    if hard_findings:
        bad("A5", f"存在「有配置项但代码另写同值字面量」的参数 = {len(hard_findings)} 个：" + "、".join(f"{n}({k}={v})" for n, k, v, _ in hard_findings))
    else:
        ok("A5", "所有已声明的数值参数在实现里都没有同值硬编码副本")

    # ---- A6 端口一致性 ----
    port_yml = placeholder_default(Y, "server.port")[0]
    mdport = re.search(r"\|\s*AAP 服务端\s*\|\s*\**(\d+)\**\s*\|", mdtext)
    client = root / "aap-client/src/api/base-url.ts"
    cport = re.search(r"127\.0\.0\.1:(\d+)", read(client)) if client.exists() else None
    got = {"yml 默认": port_yml, "docs §6.1": mdport.group(1) if mdport else None, "客户端 MP_DEV_API_BASE": cport.group(1) if cport else None}
    if len({v for v in got.values() if v}) == 1 and all(got.values()):
        ok("A6", f"端口三处一致：{got}")
    else:
        bad("A6", f"端口跨源不一致：{got}")

    # ---- A7 密钥类键不得有明文默认 ----
    # 键名按「是否承载密钥值」判定：credential 组名本身不是密钥语义（如 allow-loopback），
    # 只有 aes-key/secret/password/token/api-key/username 这类才是（坑 45：模式集要分层）。
    SECRET_KW = re.compile(r"(?i)secret|password|passwd|aes-key|api-key|token|username")
    checked, bads = 0, []
    for k, v in Y.items():
        if not SECRET_KW.search(k):
            continue
        checked += 1
        ph = placeholder_of(v)
        if ph is None:
            bads.append(f"{k} 的值不是环境变量占位（明文/字面量）")
        elif ph[1] is not None:
            bads.append(f"{k} 的占位带有默认值（缺失时不失败，静默降级）")
    if bads:
        bad("A7", f"密钥类键 {checked} 个中存在 {len(bads)} 条不安全写法：" + "；".join(bads))
    else:
        ok("A7", f"密钥类键 {checked} 个全部为无默认值的环境变量占位（缺失即启动失败，不静默）")

    # ---- A8 env 变量名比对（只比名字） ----
    env_p = Path(args.env_file)
    env_names = set()
    if env_p.exists():
        env_names = {m.group(1) for m in re.finditer(r"(?m)^\s*([A-Z_][A-Z0-9_]*)\s*=", read(env_p))}
    refs = set()
    for v in list(Y.values()) + list(T.values()):
        for m in PLACEHOLDER.finditer(v):
            if re.fullmatch(r"[A-Z][A-Z0-9_]*", m.group(1)):  # 只认环境变量形态（排除 java.io.tmpdir 等系统属性）
                refs.add(m.group(1))
    missing = sorted(r for r in refs if r not in env_names)
    ok("A8a", f"env 文件解析到 {len(env_names)} 个变量名（只输出名字，不读值）；yml 引用 {len(refs)} 个环境变量名")
    if missing:
        info(f"A8b yml 引用但 env 文件未定义（依赖内联默认，非缺陷）= {len(missing)} 个：" + "、".join(missing))
    else:
        ok("A8b", "yml 引用的环境变量名都在 env 文件里定义")

    # ---- A10 配置表（DB）与 yml 的阈值来源是否双轨 ----
    admin = root / "aap-server/src/main/java/com/hioas/aap/adminconfig"
    outside, inside = 0, 0
    for f in (root / "aap-server/src/main/java").rglob("*.java"):
        n = len(re.findall(r"aap_detection_config", read(f)))
        if n == 0:
            continue
        if admin in f.parents:
            inside += n
        else:
            outside += n
    if inside == 0:
        bad("A10a", "正向对照失败：adminconfig 里未找到 aap_detection_config（解析器/路径失效）")
    else:
        ok("A10a", f"正向对照：adminconfig 内 aap_detection_config 命中 {inside} 处（解析器真的工作了）")
    if outside == 0:
        info("A10b 管理端检测配置表（aap_detection_config/_probe：pass_score、veto_rule、weight、timeout_seconds）"
             "在 adminconfig 之外**零消费** → 发布态配置不影响检测执行与报告判定（阈值实际来自 yml + 硬编码副本）；"
             "冻结清单未声明「检测必须采用 PUBLISHED 配置」→ 列待拍板（功能范围），不判 FAIL")
    else:
        info(f"A10b 检测配置表在 adminconfig 之外有 {outside} 处消费点（与 yml 阈值双轨）")

    # ---- 输出 ----
    print()
    for x in PASSES:
        print(x)
    for x in INFOS:
        print(x)
    for x in FAILS:
        print(x)
    print()
    print(f"断言 {len(PASSES) + len(FAILS)} 条：PASS {len(PASSES)}，FAIL {len(FAILS)}；信息项 {len(INFOS)} 条")
    print("结论：" + ("存在配置项契约漂移/风险点（见 FAIL 与 INFO）" if FAILS else "配置项契约逐处一致"))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
