#!/usr/bin/env python3
"""ID 字段**对外类型**契约一致性审计（R38，只读）。

不变量：**ID 类字段（雪花 ID）对外一律是 JSON `string`**（防 JS 精度丢失）。
与 `audit-contract-keys.py`（分页集合键名）、`audit-routes.py`（方法/路径/路径变量名）、
`audit-query-params.py`（查询参数名）、`audit-error-codes.py`（错误码）、`audit-time-format.py`
（时间格式）、`audit-enum-sets.py`（枚举取值集合）、`audit-response-shape.py`（响应形状）同族，
换第十三条契约不变量：**ID 的对外类型**（skill 坑 1「ID 类型 string vs number 要逐个核对」、
坑 72「第十类可审计不变量」——R35 只做过**抽查式**核查，本工具把它机器化并可复跑）。

  简称  来源                                                          承载方式
  ----  ------------------------------------------------------------  ----------------------------------
  S     docs/backend/json-schema/**/*.schema.json                     逐属性 `type`
  O     docs/backend/openapi.yaml                                     `components.schemas` 内联属性 + `$ref` 解析
  I     aap-server/src/main/java/**/*Views.java                       响应 record 分量的 Java 类型
  C     aap-client/src/**/*.ts(x)                                     TS 字段声明的类型
  E     docs/backend/01-ER数据模型.md                                 ID 列语义（第三方裁判，信息项）
  T     aap-server/src/test/java/**/*.java                            对 ID 的字符串断言（信息项）

为什么需要它（skill 坑 43 / 72 族）：
  * 契约测试只把真实响应与 **JSON Schema** 比对 —— schema 自己写 `string` 就自洽，
    **「openapi 里同一个字段写成 number」「客户端 TS 声明成 number」「实现 record 分量是 Long」**
    这三处漂移，204 例全绿也完全看不见（openapi 与客户端 TS 都不被任何测试读取/执行）；
  * 覆盖门禁只比「方法 + 路径」；
  * 后果与坑 1 同族：客户端按 number 解析 19 位雪花 ID → **超过 2^53 后静默丢精度**，
    同一条记录在不同页面显示成两个不同的 ID（无法复现、无法定位）。

方向性（避免假发现，skill 坑 29 / 46 / 57 / 75）：
  * 每个源都配 **`> 0` 的正向对照**（A0a…A0d）：任一源解析到 0 条先怀疑解析器，不判「干净」；
  * 例外白名单是**显式**的（`channel_id`：new-api 渠道号，ER 列 bigint，非雪花），
    且设**上限 1** 的守卫（A5a）——否则「加例外」会把整条规则架空；
    例外必须在 **S 与 I 两侧都真实出现**（A5b），并有**实现注释依据**（A5c）；
  * C 侧只认「类型位置」的写法（含 `?` 可选与 `string | null` 联合），
    对象字面量里的**值位置**（`reportId: showReport ? reportId : undefined`）不算声明（坑 64 同族）。

只读保证：脚本不写任何仓库文件；收尾用 `(mtime_ns, size, md5)` 指纹自检全部被读文件未被改动（Z1）。

用法：
  python tools/audit-id-types.py [--root <dir>] [--all]
  （--root 供负向自测指向仓库外的夹具目录，skill 坑 34）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

SCHEMA_DIR = "docs/backend/json-schema"
OPENAPI = "docs/backend/openapi.yaml"
JAVA_DIR = "aap-server/src/main/java/com/hioas/aap"
CLIENT_DIR = "aap-client/src"
ER_DOC = "docs/backend/01-ER数据模型.md"
TEST_DIR = "aap-server/src/test/java"

# 字段名判据：`id` / `*_id` / `*_ids` / `ids` / 小驼峰 `*Id`（providerId、quoteId、traceId）
ID_NAME = re.compile(r"(^id$|_id$|_ids$|^ids$|^[a-z][A-Za-z]*Id$)")

# TS 字段声明的「类型位置」判据（值位置不算，坑 64）
TS_FIELD_RE = re.compile(r"^\s*(?:readonly\s+)?([A-Za-z_]\w*)(\?)?\s*:\s*([^;,\n]+?)\s*;?\s*$")
TS_TYPE_ATOM = re.compile(r"^[A-Za-z_$][\w$.]*(?:\[\])?(?:\s*\|\s*[A-Za-z_$][\w$.]*(?:\[\])?)*$")
TS_TYPE_EXPR_CHARS = set("()?:{}!=<>`+")

# Java 响应分量：`@JsonProperty("xxx") Type name,`
JAVA_COMP_RE = re.compile(
    r'@JsonProperty\("([^"]+)"\)\s+([A-Za-z_][\w.$]*(?:\s*<[^;]*?>)?)\s+(\w+)\s*[,)]'
)

# 显式例外白名单（上限 1）：非雪花的对外 ID
MAX_EXCEPTIONS = 1
EXCEPTIONS = {
    "channel_id": {
        "S": ["models/channel-binding.schema.json"],
        "I": ["SyncViews.java"],
        "依据关键词": "new-api 渠道号",
        "说明": "new-api 渠道号（ER 列 bigint、非雪花 ID）；实现注释明示「视图契约是 integer」；客户端零消费",
    },
}

NULLISH = {"null", "undefined"}


def rel_path(p: Path, root: Path) -> str:
    """仓库外路径也能显示（skill 坑 34）。"""
    try:
        return str(Path(p).resolve().relative_to(Path(root).resolve())).replace(os.sep, "/")
    except ValueError:
        return str(Path(p).resolve()).replace(os.sep, "/")


def fingerprint(paths: list[Path]) -> dict:
    out = {}
    for p in paths:
        if not p.exists():
            out[str(p)] = None
            continue
        st = p.stat()
        out[str(p)] = (st.st_mtime_ns, st.st_size, hashlib.md5(p.read_bytes()).hexdigest())
    return out


def type_repr(spec: dict) -> str:
    """JSON Schema 的 `type` → 归一字符串（去 nullish，排序）。"""
    t = spec.get("type")
    if t is None:
        return "未声明"
    parts = t if isinstance(t, list) else [t]
    keep = sorted(str(x) for x in parts if str(x) not in NULLISH)
    return "|".join(keep) if keep else "null"


class Result:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.npass = 0
        self.nfail = 0

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        tag = "PASS" if ok else "FAIL"
        if ok:
            self.npass += 1
        else:
            self.nfail += 1
        self.lines.append(f"[{tag}] {name}" + (f"：{detail}" if detail else ""))
        return ok

    def info(self, text: str) -> None:
        self.lines.append(text)


# ------------------------------------------------------------------ S：JSON Schema

def parse_schemas(root: Path) -> tuple[dict, list[Path]]:
    """→ ({(相对文件, 字段名): 类型归一}, 读过的文件)。"""
    base = root / SCHEMA_DIR
    out: dict[tuple[str, str], str] = {}
    read: list[Path] = []
    if not base.exists():
        return out, read
    for p in sorted(base.rglob("*.schema.json")):
        read.append(p)
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for name, spec in (d.get("properties") or {}).items():
            if not isinstance(spec, dict) or not ID_NAME.search(name):
                continue
            out[(rel_path(p, base), name)] = type_repr(spec)
    return out, read


# ------------------------------------------------------------------ O：openapi.yaml

def parse_openapi(root: Path) -> tuple[dict, list[str], list[str], list[Path]]:
    """→ (组件 {名: ('ref', 目标) | ('inline', {属性: 类型})}, 悬空引用, 内联 ID 属性, 读过的文件)。"""
    p = root / OPENAPI
    comps: dict[str, tuple] = {}
    dangling: list[str] = []
    inline_ids: list[str] = []
    read = [p]
    if not p.exists():
        return comps, dangling, inline_ids, read

    lines = p.read_text(encoding="utf-8").splitlines()
    i = 0
    in_schemas = False
    while i < len(lines):
        ln = lines[i]
        if re.match(r"^  schemas:\s*$", ln):
            in_schemas = True
            i += 1
            continue
        if in_schemas and re.match(r"^  \S", ln) and not re.match(r"^  schemas:", ln):
            in_schemas = False
        if in_schemas:
            m = re.match(r"^    (\w+):\s*$", ln)
            if m:
                name = m.group(1)
                kind, body, j = "empty", {}, i + 1
                while j < len(lines) and (lines[j].startswith("      ") or not lines[j].strip()):
                    s = lines[j]
                    mr = re.match(r"^      \$ref: (\S+)\s*$", s)
                    if mr:
                        kind = "ref"
                        target = mr.group(1).strip('"')
                        body = target
                        if not (root / "docs/backend" / target.replace("./", "")).exists():
                            dangling.append(f"{name} → {target}")
                    elif re.match(r"^      type: (\S+)\s*$", s):
                        if kind == "empty":
                            kind = "inline"
                        body.setdefault("type", re.match(r"^      type: (\S+)\s*$", s).group(1))
                    elif re.match(r"^      properties:\s*$", s):
                        if kind == "empty":
                            kind = "inline"
                        k = j + 1
                        while k < len(lines) and lines[k].startswith("        "):
                            mp = re.match(r"^        (\w+):\s*$", lines[k])
                            if mp:
                                prop = mp.group(1)
                                mt = re.match(r"^          type: (\S+)\s*$", lines[k + 1]) if k + 1 < len(lines) else None
                                if ID_NAME.search(prop):
                                    inline_ids.append(f"{name}.{prop}={mt.group(1) if mt else '?'}")
                            k += 1
                    j += 1
                comps[name] = (kind, body)
                i = j
                continue
        i += 1
    return comps, dangling, inline_ids, read


# ------------------------------------------------------------------ I：Java 响应视图

def parse_views(root: Path) -> tuple[dict, list[Path]]:
    """→ ({(相对文件名, 对外字段名): Java 类型}, 读过的文件)。"""
    base = root / JAVA_DIR
    out: dict[tuple[str, str], str] = {}
    read: list[Path] = []
    if not base.exists():
        return out, read
    for p in sorted(base.rglob("*Views.java")):
        read.append(p)
        txt = p.read_text(encoding="utf-8", errors="replace")
        for m in JAVA_COMP_RE.finditer(txt):
            jname, jtype = m.group(1), m.group(2).strip()
            if ID_NAME.search(jname):
                out[(p.name, jname)] = jtype
    return out, read


# ------------------------------------------------------------------ C：客户端 TS

def strip_comments(txt: str) -> str:
    """剥注释但保留字符串/模板字面量（skill 坑 58③）。"""
    out = []
    i, n = 0, len(txt)
    while i < n:
        c = txt[i]
        if c in "\"'`":
            q = c
            out.append(c)
            i += 1
            while i < n:
                if txt[i] == "\\":
                    out.append(txt[i:i + 2])
                    i += 2
                    continue
                out.append(txt[i])
                if txt[i] == q:
                    i += 1
                    break
                i += 1
            continue
        if txt.startswith("//", i):
            j = txt.find("\n", i)
            i = n if j < 0 else j
            continue
        if txt.startswith("/*", i):
            j = txt.find("*/", i)
            i = n if j < 0 else j + 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def is_ts_type(text: str) -> bool:
    """只在「类型位置」认声明：排除对象字面量的值表达式（坑 64）。"""
    if any(ch in text for ch in TS_TYPE_EXPR_CHARS):
        return False
    return bool(TS_TYPE_ATOM.match(text))


def parse_client(root: Path) -> tuple[dict, int, list[Path]]:
    """→ ({(相对文件, 字段名): TS 类型}, 原始出现处数, 读过的文件)。"""
    base = root / CLIENT_DIR
    out: dict[tuple[str, str], str] = {}
    occ = 0
    read: list[Path] = []
    if not base.exists():
        return out, occ, read
    for p in sorted(list(base.rglob("*.ts")) + list(base.rglob("*.tsx"))):
        read.append(p)
        txt = strip_comments(p.read_text(encoding="utf-8", errors="replace"))
        for ln in txt.splitlines():
            m = TS_FIELD_RE.match(ln)
            if not m:
                continue
            name, typ = m.group(1), m.group(3).strip()
            if not ID_NAME.search(name) or not is_ts_type(typ):
                continue
            occ += 1
            out[(rel_path(p, base), name)] = typ
    return out, occ, read


# ------------------------------------------------------------------ E / T：第三方裁判与信息项

def er_channel_evidence(root: Path) -> tuple[bool, str]:
    p = root / ER_DOC
    if not p.exists():
        return False, "ER 文档缺失"
    txt = p.read_text(encoding="utf-8", errors="replace")
    hit = re.search(r"channel_id`?\(new-api\)", txt)
    return bool(hit), (hit.group(0) if hit else "ER 里未标注 channel_id 的 new-api 语义")


def test_string_assertions(root: Path) -> tuple[int, list[Path]]:
    base = root / TEST_DIR
    n, read = 0, []
    if not base.exists():
        return 0, read
    pat = re.compile(r'(?:id|Id)\w*\(\)\s*\)\s*\.isEqualTo\(|"id"\s*\)\s*\.asText\(\)|\.get\("id"\)')
    for p in sorted(base.rglob("*.java")):
        read.append(p)
        n += len(pat.findall(p.read_text(encoding="utf-8", errors="replace")))
    return n, read


# ------------------------------------------------------------------ 主流程

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    s, s_read = parse_schemas(root)
    comps, dangling, inline_ids, o_read = parse_openapi(root)
    i, i_read = parse_views(root)
    c, c_occ, c_read = parse_client(root)
    er_ok, er_ev = er_channel_evidence(root)
    t_n, t_read = test_string_assertions(root)

    watched = s_read + o_read + i_read + c_read + t_read + [root / ER_DOC]
    before = fingerprint(watched)

    r = Result()
    r.info("== ID 字段对外类型契约审计（第十三类不变量；只读） ==")
    r.info(f"仓库根：{root}")

    # ---------------- A0 正向对照（坑 46 / 72 / 75） ----------------
    r.info("--- A0 正向对照：每个源都真的解析到了条目 ---")
    r.check("A0a S 解析到 ID 类字段 > 0", len(s) > 0, f"解析到 {len(s)} 条")
    n_ref = sum(1 for k, v in comps.items() if v[0] == "ref")
    n_inline = sum(1 for k, v in comps.items() if v[0] == "inline")
    r.check("A0b O 解析到组件（$ref 与内联各 > 0）", n_ref > 0 and n_inline > 0,
            f"$ref {n_ref} 个 / 内联 {n_inline} 个 / 合计 {len(comps)}")
    r.check("A0c I 解析到响应视图 ID 分量 > 0", len(i) > 0, f"唯一 (文件,字段) 对 {len(i)} 个")
    r.check("A0d C 解析到客户端 ID 类型声明 > 0", c_occ > 0,
            f"原始出现 {c_occ} 处 / 唯一 (文件,字段) 对 {len(c)} 个")
    r.check("A0e 解析器覆盖性：S 侧非空且 I 侧非空（任一为 0 先怀疑解析器）",
            len(s) > 0 and len(i) > 0, f"S={len(s)} I={len(i)}")

    # ---------------- A1 S ----------------
    r.info("--- A1 S：JSON Schema 逐属性 ID 类型必须是 string ---")
    s_bad = {f"{f}#{n}": t for (f, n), t in s.items() if t != "string"}
    s_out = {k: v for k, v in s_bad.items() if k.split("#")[1] not in EXCEPTIONS}
    r.check("A1 非 string 的 ID 字段都在例外白名单内", not s_out,
            f"越界 {len(s_out)} 条：{sorted(s_out.items())[:6]}")
    if s_bad:
        r.info(f"      · 非 string（{len(s_bad)} 条，全部为已登记例外）：{sorted(s_bad.items())}")

    # ---------------- A2 O ----------------
    r.info("--- A2 O：openapi 组件引用可解析、内联组件不得出现 ID 属性 ---")
    r.check("A2a 组件 $ref 悬空引用 = 0", not dangling, f"悬空 {len(dangling)} 条：{dangling[:5]}")
    r.check("A2b 内联组件（enum 型）里出现 ID 属性 = 0", not inline_ids,
            f"命中 {len(inline_ids)} 条：{inline_ids[:5]}")

    # ---------------- A3 I ----------------
    r.info("--- A3 I：响应视图 ID 分量的 Java 类型必须是 String ---")
    i_bad = {f"{f}#{n}": t for (f, n), t in i.items() if t != "String"}
    i_out = {k: v for k, v in i_bad.items() if k.split("#")[1] not in EXCEPTIONS}
    r.check("A3 非 String 的 ID 分量都在例外白名单内", not i_out,
            f"越界 {len(i_out)} 条：{sorted(i_out.items())[:6]}")
    if i_bad:
        r.info(f"      · 非 String（{len(i_bad)} 条，全部为已登记例外）：{sorted(i_bad.items())}")

    # ---------------- A4 C ----------------
    r.info("--- A4 C：客户端 ID 声明不得是 number ---")
    c_bad = {f"{f}#{n}": t for (f, n), t in c.items() if "string" not in t}
    r.check("A4 客户端 ID 类型声明为 number 的处数 = 0", not c_bad,
            f"越界 {len(c_bad)} 条：{sorted(c_bad.items())[:6]}")

    # ---------------- A5 例外守卫（坑 72 的「上限 1」） ----------------
    r.info("--- A5 例外白名单守卫（上限 + 双侧存在 + 实现依据）---")
    r.check(f"A5a 例外白名单条数 ≤ {MAX_EXCEPTIONS}（否则规则被架空，坑 57）",
            len(EXCEPTIONS) <= MAX_EXCEPTIONS, f"当前 {len(EXCEPTIONS)} 条")
    missing_side: dict[str, str] = {}
    for name, meta in EXCEPTIONS.items():
        for side, want in (("S", meta["S"]), ("I", meta["I"])):
            pool = s if side == "S" else i
            for f in want:
                if not any(k[0] == f and k[1] == name for k in pool):
                    missing_side[f"{name}@{side}"] = f"{f} 里没有 {name}"
    r.check("A5b 例外必须在 S 与 I 两侧都真实出现（不是凭空写的白名单）",
            not missing_side, f"缺 {len(missing_side)} 处：{missing_side}")
    no_evidence: dict[str, str] = {}
    java_all = sorted((root / JAVA_DIR).rglob("*.java")) if (root / JAVA_DIR).exists() else []
    for name, meta in EXCEPTIONS.items():
        kw = meta["依据关键词"]
        found = False
        for p in java_all:
            if kw in p.read_text(encoding="utf-8", errors="replace"):
                found = True
                break
        if not found:
            no_evidence[name] = f"实现里找不到依据关键词 {kw!r}"
    r.check("A5c 每个例外都有实现注释依据（双向取证，坑 51；搜全部实现源码而非仅 Views）",
            not no_evidence, f"无依据 {len(no_evidence)} 条：{no_evidence}（搜了 {len(java_all)} 个 .java）")

    # ---------------- A6 同名 ID 字段跨模型类型一致性（本轮新发现） ----------------
    r.info("--- A6 同名 ID 字段跨模型对外类型一致性 ---")
    by_name: dict[str, dict[str, list[str]]] = {}
    for (f, n), t in s.items():
        by_name.setdefault(n, {}).setdefault(t, []).append(f)
    multi = {n: v for n, v in by_name.items() if len(v) > 1}
    r.check("A6 同名 ID 字段在所有模型里对外类型一致", not multi,
            f"不一致 {len(multi)} 个字段名：{ {k: sorted(v) for k, v in multi.items()} }")
    for n, v in sorted(multi.items()):
        for t, files in sorted(v.items()):
            r.info(f"      · {n} = {t} ← {sorted(files)}")
    # 信息项：A6 的第二证人 —— 字符串侧的 `description` 是否自称雪花 ID（与 ER 语义不符）
    for (f, n), t in sorted(s.items()):
        if n not in multi or t != "string":
            continue
        try:
            props = json.loads((root / SCHEMA_DIR / f).read_text(encoding="utf-8")).get("properties") or {}
            desc = str((props.get(n) or {}).get("description", ""))
        except Exception:
            desc = ""
        flag = "（自称「雪花 ID」，而 ER 语义是 new-api 渠道号 → 描述与 ER 不符，信息项）" if "雪花" in desc else ""
        r.info(f"      · {f}#{n} description={desc!r}{flag}")

    # ---------------- A7 第三方裁判 ----------------
    r.info("--- A7 第三方裁判（ER 文档语义；信息项）---")
    r.check("A7 ER 文档标注 channel_id 的 new-api 语义（支撑「非雪花」判定）", er_ok, er_ev)

    r.info("--- A8 信息项（不判 FAIL）---")
    r.info(f"      · C 侧解析到 {c_occ} 处 ID 类型声明（唯一 (文件,字段) 对 {len(c)} 个）；其中含 "
           f"`string | null` 联合 {sum(1 for t in c.values() if '|' in t)} 处"
           f"（口径与 R35 抽查不同：R35 仅计单行 `name: string`）")
    r.info(f"      · T 侧对 ID 的字符串断言（信息项，口径比 R35 宽：含 `.get(\"id\")` 等）：{t_n} 处")
    r.info(f"      · 例外登记：{ {k: v['说明'] for k, v in EXCEPTIONS.items()} }")

    after = fingerprint(watched)
    changed = [k for k in before if before[k] != after.get(k)]
    r.check("Z1 全部被读文件指纹未变（脚本零写副作用）", not changed,
            f"被改写={len(changed)} 个：{changed[:3]}")

    print("\n".join(r.lines))
    print(f"\n== 断言：PASS {r.npass} / FAIL {r.nfail} ==")
    if r.nfail:
        print("结论：存在 ID 对外类型契约漂移（两套门禁都看不见：契约测试只读 JSON Schema，"
              "覆盖门禁只比方法+路径；openapi 与客户端 TS 不被任何测试读取/执行）。")
        return 1
    print("结论：ID 类字段对外类型逐处一致（S/O/I/C 四处；例外白名单 ≤ 1 且有实现依据）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
