#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R63 抽查脚本的负向自测（合成夹具，全分支反例 + 正向对照 + 注入缺陷判别力）。

纪律（每条都是本项目真实返工）：
  * 夹具目录与脚本目录**分开命名**（坑 106）；
  * 每个解析器都有 `> 0` 正向对照（坑 46/75/98/132）；空夹具必须变红并**点名**正向对照断言；
  * 注入缺陷必须**真的改到源码**（未命中锚点即空转通过，坑 66/90/94/119）；
  * 注入值与被替换值**不得有子串/词边界包含关系**（坑 90/94）；
  * 期望写成「**先跑基线，再断言 FAIL 集合恰好新增目标断言**」，且 FAIL token 取 `split()[1]`（坑 82/93/112-③）；
  * 断言比对照 `[FAIL] ` **前缀**（PASS 行也含该字符串，坑 77/82）；
  * 夹具目录零写副作用 + 真实仓库只读（关键文件 md5 不变）。
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "spotcheck-lock-R63.py"
TMP = Path("C:/Users/laitz/AppData/Local/Temp")
FIX = TMP / "aap-r63-spotcheck-fixtures"
EMPTY = TMP / "aap-r63-spotcheck-fixtures-empty"
REPO = Path("E:/workspaces/hioas/hioas-aap-001")
FAIL_RE = re.compile(r"\[FAIL\s*\]")

results = []


def chk(name, ok, detail=""):
    results.append(("PASS" if ok else "BAD", name, detail))


# ------------------------------------------------------------------ 夹具内容

MD = """# API 接口模型清单（合成夹具）

## §0 通用约定

| 项 | 约定 |
|---|---|
| 前缀 | `/api/v1` |
| 乐观锁 | 需并发保护的写支持 `If-Match: <version 或 updated_at>`；不匹配 → 409 + `E-1601` |
| 时间 | RFC3339 UTC |

## 端点（10 列表）

| ID | 方法 | 路径 | 鉴权 | 请求 | 响应 | 错误码 | 幂等/并发 | 依据 | 状态 |
|---|---|---|---|---|---|---|---|---|---|
| ALPHA-01 | PUT | `/alpha/{id}` | ✅ | body：`note` | `AlphaDetail` | E-1001 E-1104 E-1601 | `If-Match` | 真源 | T01 |
| BETA-01 | PUT | `/beta/{id}` | ✅ | body：`note` | `BetaDetail` | E-1001 E-1104 E-1601 | `If-Match` | 真源 | T01 |
| GAMMA-01 | PUT | `/gamma/{id}` | ✅ | body：`note` | `GammaDetail` | E-1001 E-1104 E-1601 | `If-Match` | 真源 | T01 |
| DELTA-01 | GET | `/delta` | ✅ | — | `DeltaDetail` | E-1406 | | 真源 | T01 |

## 端点（7 列表）

| ID | 方法 | 路径 | 角色 | 请求 | 响应 | 错误码 | 状态 |
|---|---|---|---|---|---|---|---|
| ADM-X01 | POST | `/admin/x` | SUPER_ADMIN | — | `null` | E-1601 | T02 |
"""

ENDPOINTS = {
    "total": 5,
    "endpoints": [
        {"id": "ALPHA-01", "method": "PUT", "path": "/api/v1/alpha/{id}", "response_model": "alpha-detail"},
        {"id": "BETA-01", "method": "PUT", "path": "/api/v1/beta/{id}", "response_model": "beta-detail"},
        {"id": "GAMMA-01", "method": "PUT", "path": "/api/v1/gamma/{id}", "response_model": "gamma-detail"},
        {"id": "DELTA-01", "method": "GET", "path": "/api/v1/delta", "response_model": None},
        {"id": "ADM-X01", "method": "POST", "path": "/api/v1/admin/x", "response_model": None},
    ],
}

OPENAPI = """openapi: 3.0.3
info:
  title: fixture
  version: 1.0.0
paths:
  /api/v1/alpha/{id}:
    put:
      operationId: alpha-01
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
        - name: If-Match
          in: header
          required: false
          schema:
            type: string
      responses:
        '200':
          description: 成功
  /api/v1/beta/{id}:
    put:
      operationId: beta-01
      parameters:
        - name: If-Match
          in: header
          required: false
          schema:
            type: string
      responses:
        '200':
          description: 成功
  /api/v1/gamma/{id}:
    put:
      operationId: gamma-01
      parameters:
        - name: If-Match
          in: header
          required: false
          schema:
            type: string
      responses:
        '200':
          description: 成功
  /api/v1/delta:
    get:
      operationId: delta-01
      parameters:
        - name: page
          in: query
          required: false
          schema:
            type: integer
      responses:
        '200':
          description: 成功
  /api/v1/admin/x:
    post:
      operationId: adm-x01
      responses:
        '200':
          description: 成功
"""

ERRORCODE = """package com.hioas.aap.common;

public enum ErrorCode {
    E_1001("E-1001", 400, "参数校验失败"),
    E_1104("E-1104", 409, "唯一性冲突"),
    E_1406("E-1406", 404, "资源不存在"),
    E_1601("E-1601", 409, "乐观锁版本不匹配");

    private final String code;
    private final int httpStatus;
    private final String defaultMessage;

    ErrorCode(String code, int httpStatus, String defaultMessage) {
        this.code = code;
        this.httpStatus = httpStatus;
        this.defaultMessage = defaultMessage;
    }
}
"""

CTRL = """package com.hioas.aap.%(pkg)s;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/%(lower)s")
public class %(Cap)sController {

    private final %(Cap)sService %(lower)sService;

    public %(Cap)sController(%(Cap)sService %(lower)sService) {
        this.%(lower)sService = %(lower)sService;
    }

    /** %(ID)s 保存（支持 If-Match 乐观锁）。 */
    @PutMapping("/{id}")
    public ApiEnvelope<%(Cap)sViews.Detail> update(@PathVariable Long id,
                                                   @RequestBody %(Cap)sCommand command,
                                                   @RequestHeader(value = "If-Match", required = false) String ifMatch) {
        return ApiEnvelope.ok(%(lower)sService.update(id, command, ifMatch));
    }
}
"""

SVC = """package com.hioas.aap.%(pkg)s;

import org.springframework.stereotype.Service;

@Service
public class %(Cap)sService {

    /** %(ID)s 保存；If-Match 与当前 version 不一致 → E-1601。 */
    public %(Cap)sViews.Detail update(Long id, %(Cap)sCommand command, String ifMatch) {
        %(Cap)sEntity entity = load(id);
        if (ifMatch != null && !ifMatch.isBlank()
                && !ifMatch.trim().equals(String.valueOf(entity.getVersion()))) {
            throw new ApiException(ErrorCode.E_1601, "已被更新，请刷新后重试");
        }
        return null;
    }
}
"""

VIEWS = """package com.hioas.aap.%(pkg)s;

public final class %(Cap)sViews {

    public record Detail(Long id, Integer version, String note) {
    }
}
"""

CLIENT = """import { http } from './http';

const path = (id: string) => `/%(lower)s/${encodeURIComponent(id)}`;

export function save%(Cap)s(id: string, etag: string, note: string) {
  return http<%(Cap)sDetail>(path(id), { method: 'PUT', headers: { 'If-Match': etag }, data: { note } });
}
"""

TEST = """package com.hioas.aap.%(pkg)s;

class %(Cap)sContractTest {

    @Test
    @DisplayName("%(ID)s If-Match 过期 → 409 E-1601（不覆盖他人改动）")
    void optimisticLock() throws Exception {
        String token = token(PHONE);
        HttpResult stale = send("PUT", "/%(lower)s/1", "{}", token, Map.of("If-Match", "0"));
        assertThat(stale.status()).isEqualTo(409);
        assertThat(stale.code()).isEqualTo("E-1601");
    }
}
"""

SCHEMA = """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "id": {"type": "string"},
    "version": {"type": "integer"},
    "note": {"type": "string"}
  }
}
"""


def build_fixture(d: Path):
    if d.exists():
        shutil.rmtree(d)
    (d / "tools").mkdir(parents=True)
    shutil.copy2(REPO / "tools/audit-routes.py", d / "tools/audit-routes.py")
    (d / "docs/backend/json-schema/models").mkdir(parents=True)
    (d / "docs/backend/02-API接口模型清单.md").write_text(MD, encoding="utf-8", newline="\n")
    (d / "docs/backend/endpoints.json").write_text(
        json.dumps(ENDPOINTS, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    (d / "docs/backend/openapi.yaml").write_text(OPENAPI, encoding="utf-8", newline="\n")
    for name in ("alpha", "beta", "gamma"):
        (d / ("docs/backend/json-schema/models/%s-detail.schema.json" % name)).write_text(
            SCHEMA, encoding="utf-8", newline="\n")
    common = d / "aap-server/src/main/java/com/hioas/aap/common"
    common.mkdir(parents=True)
    (common / "ErrorCode.java").write_text(ERRORCODE, encoding="utf-8", newline="\n")
    for name, eid in (("alpha", "ALPHA-01"), ("beta", "BETA-01"), ("gamma", "GAMMA-01")):
        pkg = d / "aap-server/src/main/java/com/hioas/aap" / name
        pkg.mkdir(parents=True, exist_ok=True)
        ctx = {"pkg": name, "lower": name, "Cap": name.capitalize(), "ID": eid}
        (pkg / ("%sController.java" % name.capitalize())).write_text(CTRL % ctx, encoding="utf-8", newline="\n")
        (pkg / ("%sService.java" % name.capitalize())).write_text(SVC % ctx, encoding="utf-8", newline="\n")
        (pkg / ("%sViews.java" % name.capitalize())).write_text(VIEWS % ctx, encoding="utf-8", newline="\n")
        t = d / "aap-server/src/test/java/com/hioas/aap" / name
        t.mkdir(parents=True, exist_ok=True)
        (t / ("%sContractTest.java" % name.capitalize())).write_text(TEST % ctx, encoding="utf-8", newline="\n")
        c = d / "aap-client/src/api"
        c.mkdir(parents=True, exist_ok=True)
        (c / ("%s.ts" % name)).write_text(CLIENT % ctx, encoding="utf-8", newline="\n")
    admin = d / "aap-server/src/main/java/com/hioas/aap/admin"
    admin.mkdir(parents=True, exist_ok=True)
    (admin / "AdminXController.java").write_text(
        'package com.hioas.aap.admin;\n\n@RestController\n@RequestMapping("/api/v1/admin")\n'
        'public class AdminXController {\n\n    @PostMapping("/x")\n'
        '    public ApiEnvelope<Void> doX() {\n        return ApiEnvelope.ok(null);\n    }\n}\n',
        encoding="utf-8", newline="\n")
    delta = d / "aap-server/src/main/java/com/hioas/aap/delta"
    delta.mkdir(parents=True, exist_ok=True)
    (delta / "DeltaController.java").write_text(
        'package com.hioas.aap.delta;\n\n@RestController\n@RequestMapping("/api/v1/delta")\n'
        'public class DeltaController {\n\n    @GetMapping\n'
        '    public ApiEnvelope<DeltaViews.Detail> list(@RequestParam("page") int page) {\n'
        '        return ApiEnvelope.ok(null);\n    }\n}\n',
        encoding="utf-8", newline="\n")


# ------------------------------------------------------------------ 工具

def run(d: Path):
    p = subprocess.run([sys.executable, str(SCRIPT), "--root", str(d)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def fails(text):
    """FAIL 断言 token 集合（取 split()[1]，坑 112-③）；[PASS] 行排除（坑 77/109）。"""
    out = set()
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("[PASS]"):
            continue
        if FAIL_RE.search(s):
            parts = s.split()
            if len(parts) >= 2:
                out.add(parts[1])
    return out


def mutate(d: Path, rel: str, old: str, new: str, count=-1):
    """→ 命中次数（0 = 锚点失效 → 空转通过，坑 66/90/94）。"""
    p = d / rel
    t = p.read_text(encoding="utf-8")
    n = t.count(old)
    if n == 0:
        return 0
    t = t.replace(old, new) if count < 0 else t.replace(old, new, count)
    p.write_text(t, encoding="utf-8", newline="\n")
    return n


def copy_fixture(tag: str) -> Path:
    d = TMP / ("aap-r63-inj-" + tag)
    if d.exists():
        shutil.rmtree(d)
    shutil.copytree(FIX, d)
    return d


def fingerprint(d: Path):
    out = {}
    for p in sorted(d.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(d))] = hashlib.md5(p.read_bytes()).hexdigest()
    return out


# ------------------------------------------------------------------ 主流程

def main():
    build_fixture(FIX)
    if EMPTY.exists():
        shutil.rmtree(EMPTY)
    (EMPTY / "tools").mkdir(parents=True)
    shutil.copy2(REPO / "tools/audit-routes.py", EMPTY / "tools/audit-routes.py")

    repo_files = [REPO / "docs/backend/02-API接口模型清单.md", REPO / "docs/backend/endpoints.json",
                  REPO / "docs/backend/openapi.yaml",
                  REPO / "aap-server/src/main/java/com/hioas/aap/common/ErrorCode.java",
                  REPO / "aap-server/src/main/java/com/hioas/aap/provider/ProviderService.java",
                  REPO / "aap-server/src/main/java/com/hioas/aap/quote/QuoteService.java"]
    repo_before = {str(p): hashlib.md5(p.read_bytes()).hexdigest() for p in repo_files}
    fix_before = fingerprint(FIX)

    # 1) 合规夹具：rc=0 且 FAIL 0，且 A0a…A0i 全 PASS
    rc, out = run(FIX)
    base = fails(out)
    a0 = ["A0" + c for c in "abcdefghi"]
    a0_missing = [t for t in a0 if ("[PASS] %s " % t) not in out]
    chk("合规夹具 rc=0", rc == 0, "rc=%d" % rc)
    chk("合规夹具 FAIL 0（基线干净，坑 82/93/136）", not base, "FAIL=%s" % sorted(base))
    chk("合规夹具 A0a…A0i 九条正向对照全 PASS", not a0_missing, "缺=%s" % a0_missing)
    chk("合规夹具汇总行 PASS/FAIL 可解析", ("汇总 PASS " in out), out.strip().splitlines()[-2] if out else "")

    # 2) 空夹具：必须变红并点名全部解析器正向对照
    rc2, out2 = run(EMPTY)
    f2 = fails(out2)
    chk("空夹具 rc!=0", rc2 != 0, "rc=%d" % rc2)
    chk("空夹具点名全部 A0* 正向对照", set(a0) <= f2, "FAIL=%s" % sorted(f2))
    chk("空夹具条件化断言一并转红（A2b/A4/A8/A9/A10）",
        {"A2b", "A4", "A8", "A9", "A10"} <= f2, "FAIL=%s" % sorted(f2))

    # 3) 注入缺陷：先跑基线，再断言 FAIL 集合恰好新增目标断言
    inj = [
        ("md-s0-header", "docs/backend/02-API接口模型清单.md", "`If-Match: <version", "`If_Match: <version", {"A1"}),
        ("md-row-header", "docs/backend/02-API接口模型清单.md", "E-1001 E-1104 E-1601 | `If-Match` | 真源 | T01 |\n| BETA-01", "E-1001 E-1104 E-1601 | | 真源 | T01 |\n| BETA-01", {"A3"}),
        ("md-row-code", "docs/backend/02-API接口模型清单.md", "| ALPHA-01 | PUT | `/alpha/{id}` | ✅ | body：`note` | `AlphaDetail` | E-1001 E-1104 E-1601 |", "| ALPHA-01 | PUT | `/alpha/{id}` | ✅ | body：`note` | `AlphaDetail` | E-1001 E-1104 |", {"A2b", "A4"}),
        ("impl-code", "aap-server/src/main/java/com/hioas/aap/alpha/AlphaService.java", "ErrorCode.E_1601", "ErrorCode.E_1104", {"A2"}),
        ("errcode-status", "aap-server/src/main/java/com/hioas/aap/common/ErrorCode.java", 'E_1601("E-1601", 409', 'E_1601("E-1601", 403', {"A6"}),
        ("client-header", "aap-client/src/api/alpha.ts", "'If-Match'", "'If-None-Match'", {"A7"}),
        ("openapi-header", "docs/backend/openapi.yaml", "in: header", "in: cookie", {"A10"}),
        ("test-header", "aap-server/src/test/java/com/hioas/aap/alpha/AlphaContractTest.java", '"If-Match"', '"If-None-Match"', {"A9"}),
        ("schema-token", "docs/backend/json-schema/models/alpha-detail.schema.json", '"version": {"type": "integer"},', "", {"A8"}),
    ]
    for tag, rel, old, new, expect in inj:
        d = copy_fixture(tag)
        if tag == "client-header":
            n = 0
            for f in ("alpha.ts", "beta.ts", "gamma.ts"):
                n += mutate(d, "aap-client/src/api/" + f, old, new)
        else:
            n = mutate(d, rel, old, new)
        chk("注入 %s 锚点命中（未命中即空转通过，坑 66/90/94）" % tag, n > 0, "命中=%d" % n)
        rcx, outx = run(d)
        delta = fails(outx) - base
        gone = base - fails(outx)
        chk("注入 %s → FAIL 集合恰好新增 %s" % (tag, sorted(expect)),
            delta == expect and not gone, "delta=%s gone=%s rc=%d" % (sorted(delta), sorted(gone), rcx))
        chk("注入 %s → 合规夹具的 A0* 正向对照未被打红（夹具留第二来源兜底，坑 136）" % tag,
            not (set(a0) & delta), "delta=%s" % sorted(delta))

    # 4) md 全端点行删除（宽注入）：A0b + 全部条件化断言转红
    d = copy_fixture("md-all-rows")
    t = (d / "docs/backend/02-API接口模型清单.md").read_text(encoding="utf-8")
    kept = "\n".join(ln for ln in t.splitlines()
                     if not re.match(r"^\| (ALPHA|BETA|GAMMA|DELTA)-", ln))
    (d / "docs/backend/02-API接口模型清单.md").write_text(kept, encoding="utf-8", newline="\n")
    n = 4 if len(kept) < len(t) else 0
    chk("注入 md-all-rows 锚点命中", n > 0, "命中=%d" % n)
    rcx, outx = run(d)
    delta = fails(outx) - base
    chk("注入 md-all-rows → 恰好新增 {A0b,A2b,A3,A4,A8,A9,A10}",
        delta == {"A0b", "A2b", "A3", "A4", "A8", "A9", "A10"} and not (base - fails(outx)),
        "delta=%s rc=%d" % (sorted(delta), rcx))

    # 5) 零写副作用 + 真实仓库只读
    chk("夹具目录零写副作用（脚本只读）", fingerprint(FIX) == fix_before, "被改写文件数=%d"
        % sum(1 for k in set(fix_before) | set(fingerprint(FIX))
              if fix_before.get(k) != fingerprint(FIX).get(k)))
    repo_after = {str(p): hashlib.md5(p.read_bytes()).hexdigest() for p in repo_files}
    chk("真实仓库关键文件 md5 未变（脚本只读）", repo_after == repo_before,
        "被改写=%s" % [k for k in repo_before if repo_before[k] != repo_after.get(k)])

    npass = sum(1 for lvl, _, _ in results if lvl == "PASS")
    nbad = sum(1 for lvl, _, _ in results if lvl == "BAD")
    print("== R63 抽查负向自测（%d 条断言） ==" % len(results))
    print("夹具目录：%s" % FIX)
    print("空夹具目录：%s" % EMPTY)
    print("")
    for lvl, name, detail in results:
        if lvl == "BAD":
            print("[BAD ] %s | %s" % (name, detail))
    print("")
    print("自测汇总：OK %d / BAD %d" % (npass, nbad))
    return 0 if nbad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
