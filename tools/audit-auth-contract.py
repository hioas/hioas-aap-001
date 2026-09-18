#!/usr/bin/env python3
"""鉴权级别契约一致性审计（R30，只读）。

不变量：**每个端点的鉴权要求**必须在五处真源逐端点一致 —— 与 `audit-contract-keys.py`
（分页集合键名）、`audit-error-codes.py`（错误码）同族，换第三条契约不变量：**认证/授权级别**。

  简称  来源                                                          承载方式
  ----  ------------------------------------------------------------  ----------------------------------
  M     docs/backend/endpoints.json                                  逐端点 `auth`（anon / authenticated / 角色列表）
  I     aap-server/src/main/java/**/*Controller.java                   类级/方法级 `@PreAuthorize` + 映射注解 → 逐路由角色集
  S     aap-server/.../config/SecurityConfig.java                      `PUBLIC_PATHS` 匿名白名单
  O     docs/backend/openapi.yaml                                     每 operation `security: []`（匿名）或 bearerAuth
  D     docs/backend/02-API接口模型清单.md                            逐行「鉴权」列（10 列）或「角色」列（7 列）

为什么需要它（skill 坑 43 / 49 族）：204 例契约测试只校验 JSON Schema（**schema 里没有鉴权**），
覆盖门禁只证明「路由已注册」（**不看授权注解**）→ 清单写着「仅超管」而实现漏了 `@PreAuthorize`
（越权）或反之（误拒），**两套门禁全绿也完全看不见**。

别名归一：`SUPPLIER` ≡ `PROVIDER`（注册语义 role=SUPPLIER，清单口径写 PROVIDER，见 AuthService/AuthPrincipal）。

只读保证：脚本不写任何仓库文件；收尾用 `(mtime_ns, size, md5)` 指纹自检全部被读文件未被改动。

用法：
  python tools/audit-auth-contract.py [--root <dir>]
  （--root 供负向自测指向仓库外的夹具目录；默认 = 本脚本上一级目录）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

REL_STATIC = [
    "docs/backend/endpoints.json",
    "docs/backend/openapi.yaml",
    "docs/backend/02-API接口模型清单.md",
    "aap-server/src/main/java/com/hioas/aap/config/SecurityConfig.java",
]
CONTROLLER_DIR = "aap-server/src/main/java/com/hioas/aap"

# 角色别名：注册语义写 SUPPLIER，冻结清单口径写 PROVIDER（同一主体类型）
ROLE_ALIAS = {"SUPPLIER": "PROVIDER"}
# 清单 auth 里的非角色取值
AUTH_ANON = "anon"
AUTH_AUTHENTICATED = "authenticated"

VAR_RE = re.compile(r"\{[^}]+\}")
MAPPING_RE = re.compile(r"@(Get|Post|Put|Delete|Patch)Mapping\b")
REQ_MAPPING_RE = re.compile(r"@RequestMapping\s*\(([^)]*)\)")
PREAUTH_RE = re.compile(r"@PreAuthorize\s*\(\s*\"([^\"]*)\"\s*\)")
HASANYROLE_RE = re.compile(r"hasAnyRole\s*\(([^)]*)\)")
HASROLE_RE = re.compile(r"hasRole\s*\(([^)]*)\)")
CLASS_DECL_RE = re.compile(r"^[A-Za-z@\s]*\bclass\s+\w+", re.MULTILINE)


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


def norm_path(path: str) -> str:
    return VAR_RE.sub("{}", path.strip())


def norm_roles(roles: set[str]) -> frozenset:
    return frozenset(ROLE_ALIAS.get(r, r) for r in roles)


def roles_from_expr(expr: str) -> set[str]:
    """从 @PreAuthorize 表达式抽出角色集合（本项目只有 hasRole / hasAnyRole 两种形态）。"""
    out: set[str] = set()
    for m in HASANYROLE_RE.finditer(expr):
        out.update(re.findall(r"'([^']+)'", m.group(1)))
    for m in HASROLE_RE.finditer(expr):
        out.update(re.findall(r"'([^']+)'", m.group(1)))
    return out


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


# ---------------------------------------------------------------- M：清单

def parse_manifest(p: Path) -> tuple[int, dict[str, str]]:
    data = json.loads(p.read_text(encoding="utf-8"))
    total = int(data.get("total", len(data.get("endpoints", []))))
    return total, {e["id"]: (e.get("auth") or "").strip() for e in data["endpoints"]}


def manifest_route_map(p: Path) -> dict[str, tuple[str, str]]:
    data = json.loads(p.read_text(encoding="utf-8"))
    return {e["id"]: (e["method"].upper(), norm_path(e["path"])) for e in data["endpoints"]}


def manifest_roles(auth: str) -> set[str]:
    if auth in (AUTH_ANON, AUTH_AUTHENTICATED, ""):
        return set()
    return {t.strip() for t in auth.split(",") if t.strip()}


# ---------------------------------------------------------------- S：SecurityConfig

def parse_public_paths(p: Path) -> set[str]:
    text = p.read_text(encoding="utf-8")
    m = re.search(r"PUBLIC_PATHS\s*=\s*\{(.*?)\};", text, re.DOTALL)
    if not m:
        return set()
    return {s for s in re.findall(r'"([^"]+)"', m.group(1))}


# ---------------------------------------------------------------- I：控制器 → 路由角色

def class_body_start(text: str) -> int:
    m = CLASS_DECL_RE.search(text)
    if not m:
        return -1
    brace = text.find("{", m.end())
    return brace if brace >= 0 else -1


def class_prefix(text: str, body: int) -> str:
    """类级 @RequestMapping 前缀（取类声明之前的最后一个）。"""
    prefix = ""
    for m in REQ_MAPPING_RE.finditer(text[:body]):
        vals = re.findall(r'"([^"]*)"', m.group(1))
        if vals:
            prefix = vals[0]
    return prefix


def body_brace(text: str, idx: int) -> int:
    """从注解起点找到**方法体起始 `{`**；字符串里的括号同样计数（平衡）故不会误判。

    必须跳过注解参数里的 `{`（`@GetMapping("/{id}")`），否则会把路径变量当方法体（真实返工：
    第一版用 `text.find("{", idx)` → 所有 `/{id}` 端点的方法级 `@PreAuthorize` 全部解析丢失，
    22 条端点报出「清单有角色、实现为空」的**假发现**）。
    """
    depth = 0
    k = idx
    n = len(text)
    while k < n:
        c = text[k]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == "{" and depth == 0:
            return k
        elif c == ";" and depth == 0:
            return -1
        k += 1
    return -1


def method_roles(text: str, body: int, idx: int, class_roles: set[str]) -> set[str]:
    """方法级 @PreAuthorize 优先；无则继承类级。

    本项目实际写法是**映射注解在前、@PreAuthorize 在后**（`@GetMapping` 换行 `@PreAuthorize(...)`），
    故先看注解之后的注解区（到方法体 `{` 为止）；再兼容另一种顺序（注解之前、到上一个 `}`/`;` 为止）。
    """
    end = body_brace(text, idx)
    after = text[idx:end] if end > 0 else text[idx:idx + 600]
    m = PREAUTH_RE.search(after)
    if m:
        return roles_from_expr(m.group(1))
    last = None
    for mm in PREAUTH_RE.finditer(text, body, idx):
        last = mm
    if last is not None:
        tail = text[last.end():idx]
        if "}" not in tail and ";" not in tail:
            return roles_from_expr(last.group(1))
    return set(class_roles)


def parse_controllers(ctrl_dir: Path) -> tuple[dict[tuple[str, str], set[str]], list[str]]:
    """→ {(METHOD, 归一路径): 角色集合}；无 @PreAuthorize 的记为空集合（= 任意已认证）。"""
    routes: dict[tuple[str, str], set[str]] = {}
    problems: list[str] = []
    for f in sorted(ctrl_dir.rglob("*Controller.java")):
        text = f.read_text(encoding="utf-8")
        body = class_body_start(text)
        if body < 0:
            continue
        prefix = class_prefix(text, body)
        cls_pre = [m for m in PREAUTH_RE.finditer(text[:body])]
        class_roles = roles_from_expr(cls_pre[-1].group(1)) if cls_pre else set()
        found = False
        for m in MAPPING_RE.finditer(text):
            if m.start() < body:
                continue
            method = m.group(1).upper()
            seg = text[m.end():text.find(")", m.end()) + 1] if ")" in text[m.end():] else ""
            paths = re.findall(r'"([^"]*)"', seg)
            sub = paths[0] if paths else ""
            full = norm_path((prefix + sub) or prefix)
            key = (method, full)
            roles = method_roles(text, body, m.start(), class_roles)
            if key in routes and routes[key] != roles:
                problems.append(f"{f.name}: 路由重复且角色不一致 {key}")
            routes[key] = roles
            found = True
        if not found:
            problems.append(f"{f.name}: 类内有 @RequestMapping 但未解析到任何方法级映射")
    return routes, problems


# ---------------------------------------------------------------- O：openapi

def parse_openapi_security(text: str) -> dict[str, bool]:
    """→ {operationId: 是否匿名（security: []）}。缩进必须逐层校验（坑 44）。"""
    out: dict[str, bool] = {}
    cur = None
    for ln in text.splitlines():
        m = re.match(r"^      operationId: (\S+)\s*$", ln)
        if m:
            cur = m.group(1)
            out.setdefault(cur, False)
            continue
        if cur is None:
            continue
        if re.match(r"^      security: \[\]\s*$", ln):
            out[cur] = True
        elif re.match(r"^      security:\s*$", ln):
            out[cur] = False
    return out


# ---------------------------------------------------------------- D：md 清单

def split_row(ln: str) -> list[str]:
    """按**未被转义**的 `|` 切分（坑 48）。"""
    cells = re.split(r"(?<!\\)\|", ln.strip("|"))
    return [c.replace("\\|", "|").strip() for c in cells]


def parse_md_auth(p: Path) -> tuple[dict[str, str], list[str]]:
    """→ {ID: 归一后的鉴权取值}（`anon` / `authenticated` / 空格分隔的角色 token 串）。

    两套表头（坑 49）：10 列的表头是「鉴权」，7 列的表头是「角色」；`同上` 必须继承**上一行**取值。
    """
    rows: dict[str, str] = {}
    problems: list[str] = []
    header: list[str] | None = None
    last_cell: str | None = None
    for raw in p.read_text(encoding="utf-8").splitlines():
        ln = raw.strip()
        if not ln.startswith("|"):
            continue
        cells = split_row(ln)
        if cells and cells[0] == "ID":
            header = cells
            last_cell = None
            continue
        if header is None:
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        if len(cells) != len(header):
            continue
        row_id = cells[0]
        if not re.match(r"^[A-Z]+-[A-Z0-9]+$", row_id):
            continue
        col = "鉴权" if "鉴权" in header else ("角色" if "角色" in header else None)
        if col is None:
            problems.append(f"{row_id}: 当前表头无「鉴权」/「角色」列（列序定位失败）")
            continue
        cell = cells[header.index(col)]
        if cell == "同上":
            if last_cell is None:
                problems.append(f"{row_id}: `同上` 无上一行可继承")
                continue
            cell = last_cell
        last_cell = cell
        if cell == "免":
            rows[row_id] = AUTH_ANON
        elif cell.startswith("✅"):
            rows[row_id] = AUTH_AUTHENTICATED
        else:
            rows[row_id] = " ".join(re.findall(r"[A-Z_]{3,}", cell))
    return rows, problems


def md_roles(value: str) -> set[str]:
    if value in (AUTH_ANON, AUTH_AUTHENTICATED, ""):
        return set()
    return {t for t in value.split() if t}


# ---------------------------------------------------------------- 主流程

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--all", action="store_true", help="列出全部漂移明细（默认只列前 12 条）")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    paths = {k: root / r for k, r in zip(["M", "O", "D", "S"], REL_STATIC)}
    ctrl_dir = root / CONTROLLER_DIR

    missing = [k for k, p in paths.items() if not p.exists()]
    if not ctrl_dir.exists():
        missing.append("I=" + str(ctrl_dir))
    if missing:
        print("[FAIL] 源文件缺失：" + ", ".join(f"{k}={paths[k] if k != 'I' else ctrl_dir}" for k in missing))
        return 1

    watched = list(paths.values()) + sorted(ctrl_dir.rglob("*.java"))
    before = fingerprint(watched)

    r = Result()
    r.info(f"根目录：{str(root).replace(os.sep, '/')}（仓库外路径也照常显示，skill 坑 34）")

    total, m_auth = parse_manifest(paths["M"])
    m_route = manifest_route_map(paths["M"])
    o_sec = parse_openapi_security(paths["O"].read_text(encoding="utf-8"))
    public = parse_public_paths(paths["S"])
    impl, i_problems = parse_controllers(ctrl_dir)
    d_auth, d_problems = parse_md_auth(paths["D"])

    r.info("--- 正向对照（解析器真的解析到了）---")
    r.check("A0a M 端点数 = total", total > 0 and len(m_auth) == total, f"total={total} parsed={len(m_auth)}")
    r.check("A0b D 行数 = total", len(d_auth) == total, f"parsed={len(d_auth)} 期望={total}")
    r.check("A0c O operation 数 = total", len(o_sec) == total, f"parsed={len(o_sec)} 期望={total}")
    r.check("A0d I 解析到控制器路由", len(impl) > 0, f"parsed={len(impl)} 条路由，控制器问题 {len(i_problems)} 条")
    r.check("A0e S 解析到匿名白名单", len(public) > 0, f"parsed={sorted(public)}")
    r.check("A0f I 解析无异常", not i_problems, "; ".join(i_problems[:5]))

    r.info("--- 逐端点：清单 ⇔ 实现路由 ⇔ 匿名白名单 ⇔ openapi ⇔ md ---")
    unlocated = sorted(eid for eid, key in m_route.items() if key not in impl)
    r.check("A1 清单每条端点都能在实现里定位到路由（解析器覆盖性正向对照）", not unlocated,
            f"未定位 {len(unlocated)} 条：{unlocated[:10]}")

    anon_m = {eid for eid, a in m_auth.items() if a == AUTH_ANON}
    anon_o = {eid for eid, is_anon in o_sec.items() if is_anon}
    r.check("A2 openapi `security: []` 集合 = 清单 anon 集合", anon_m == anon_o,
            f"清单 {len(anon_m)} 条 / openapi {len(anon_o)} 条；差集={sorted(anon_m ^ anon_o)}")

    wrong_public = {eid: m_route[eid][1] for eid in sorted(anon_m) if m_route[eid][1] not in public}
    r.check("A3a 清单 anon 的端点都在 SecurityConfig.PUBLIC_PATHS 里", not wrong_public, f"{wrong_public}")
    leaked = {eid: m_route[eid][1] for eid, a in sorted(m_auth.items())
              if a != AUTH_ANON and m_route[eid][1] in public}
    r.check("A3b 非 anon 的端点都不在 PUBLIC_PATHS 里（否则等于匿名可访问）", not leaked, f"{leaked}")

    anon_with_preauth = {eid: sorted(impl.get(m_route[eid], set())) for eid in sorted(anon_m)
                         if impl.get(m_route[eid])}
    r.check("A4 anon 端点上没有 @PreAuthorize（清单说免，实现不得再要求角色）", not anon_with_preauth,
            f"{anon_with_preauth}")

    role_drift: dict[str, dict] = {}
    for eid in sorted(m_auth):
        a = m_auth[eid]
        if a in (AUTH_ANON, AUTH_AUTHENTICATED, ""):
            continue
        key = m_route[eid]
        if key not in impl:
            continue
        want, got = norm_roles(manifest_roles(a)), norm_roles(impl[key])
        if want != got:
            role_drift[eid] = {"清单": sorted(want), "实现": sorted(got)}
    r.check("A5 清单角色集合 = 实现 @PreAuthorize 角色集合（逐端点，别名归一）", not role_drift,
            f"不一致 {len(role_drift)} 条")
    if role_drift:
        for eid, d in (list(role_drift.items()) if args.all else list(role_drift.items())[:12]):
            r.info(f"      · {eid}: 清单={d['清单']} 实现={d['实现']}")

    auth_only = sorted(eid for eid, a in m_auth.items() if a == AUTH_AUTHENTICATED)
    auth_restricted = {eid: sorted(impl.get(m_route[eid], set())) for eid in auth_only if impl.get(m_route[eid])}
    r.check("A6 清单 `authenticated` 的端点实现里不带角色限制（= 任意已认证）", not auth_restricted,
            f"越权收窄 {auth_restricted}；清单共 {len(auth_only)} 条 {auth_only}")

    md_anon_drift = {eid: d_auth.get(eid) for eid in sorted(m_auth)
                     if (m_auth[eid] == AUTH_ANON) != (d_auth.get(eid) == AUTH_ANON)}
    r.check("A7 md 的 `免` 行集合 = 清单 anon 集合", not md_anon_drift, f"不一致 {md_anon_drift}")

    md_role_drift = {}
    for eid in sorted(m_auth):
        if m_auth[eid] in (AUTH_ANON, AUTH_AUTHENTICATED, ""):
            continue
        mdv = d_auth.get(eid, "")
        if mdv == AUTH_AUTHENTICATED:
            continue      # 10 列表头只写 ✅（不列角色），由 A7/A5 覆盖
        want, got = norm_roles(manifest_roles(m_auth[eid])), norm_roles(md_roles(mdv))
        if want != got:
            md_role_drift[eid] = {"清单": sorted(want), "md": sorted(got)}
    r.check("A8 md「角色」列 = 清单角色集合（仅逐条列角色的 7 列表头行）", not md_role_drift,
            f"不一致 {len(md_role_drift)} 条")
    if md_role_drift:
        for eid, d in (list(md_role_drift.items()) if args.all else list(md_role_drift.items())[:12]):
            r.info(f"      · {eid}: 清单={d['清单']} md={d['md']}")

    r.check("A9 md 表头定位无异常", not d_problems, "; ".join(d_problems[:5]))

    r.info("--- 零写副作用自检 ---")
    after = fingerprint(watched)
    changed = [rel_path(Path(k), root) for k in before if before[k] != after[k]]
    r.check("Z1 全部被读文件指纹未变（脚本零写副作用）", not changed, f"被改写={len(changed)} 个：{changed[:5]}")

    print("\n".join(r.lines))
    print(f"\n断言 {r.npass + r.nfail} 条：PASS {r.npass}，FAIL {r.nfail}")
    return 0 if r.nfail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
