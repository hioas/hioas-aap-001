#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R59 抽查脚本的负向自测（判别力实测）—— 只读真实仓库，只写自己的夹具目录。

覆盖（坑 46/66/75/82/90/93/94 的纪律）：
  T1-T5  合规夹具：rc=0 且 FAIL 0 + 全部正向对照 PASS + 夹具目录零写副作用
  T6-T7  空夹具必须转红并点名 A0a（解析器失效不得判绿）
  T8-T9  注入1 openapi 把 text/html 端点声明成 application/json → **恰好**新增 A2b
  T10-T11 注入2 实现 produces 改成 JSON（openapi 不变）→ 恰好新增 {A2b, A3a}
  T12-T13 注入3 控制器加 @ResponseStatus(HttpStatus.CREATED) → 恰好新增 A1c
  T14-T15 注入4 客户端新增对非包络端点的调用点 → 恰好新增 A4a
  T16-T17 注入5 md §4 成功行改成 201 → 恰好新增 A6b（md↔openapi 状态维度有判别力）
  T18    每次注入都必须「真的改到源码」（锚点未命中即失败，坑 66/94）
  T19-T20 真实仓库只读（git status 不变）+ 真实仓库 FAIL 集合恰好 = {A2b}

脚本放 <tmp>/aap-r59-spotcheck/，夹具放 <tmp>/aap-r59-spotcheck-fixtures/（坑 106：不能同目录）。
"""
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(r"C:/Users/laitz/AppData/Local/Temp/aap-r59-spotcheck/spotcheck-success-shape-R59.py")
FIX = Path(r"C:/Users/laitz/AppData/Local/Temp/aap-r59-spotcheck-fixtures")
REAL = Path(r"E:/workspaces/hioas/hioas-aap-001")

MD = """# 接口清单（夹具）

## 0. 通用约定（所有接口）

| 项 | 约定 |
|---|---|
| 响应包体 | `{"code":"0|E-xxxx","message":"...","data":{...},"traceId":"..."}` |

## 1. 供应商端接口

| ID | 方法 | 路径 | 鉴权 | 请求 | 响应 | 错误码 | 幂等/并发 | 依据 | 状态 |
|---|---|---|---|---|---|---|---|---|---|
| SYN-01 | GET | `/syn/list` | ✅ | q：`page` | `{items:[],page,pageSize,total}` | E-1901 | | 真源 | T99 |
| SYN-02 | GET | `/syn/{id}/html` | ✅ | — | `text/html` | E-1401 | | 推断 | T99 |

## 4. 错误码表（统一响应 `code`）

| 码 | HTTP | 场景 | 依据 |
|---|---|---|---|
| `0` | 200 | 成功 | |
| `E-1401` | 404 | 资源不存在 | |
"""

CONTROLLER_JSON = """package syn;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;

@RequestMapping("/api/v1/syn")
public class SynController {

    @GetMapping
    public ApiEnvelope<Object> list() {
        return ApiEnvelope.ok(null);
    }
}
"""

CONTROLLER_HTML = """package syn;

import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;

@RequestMapping("/api/v1/syn")
public class SynHtmlController {

    @GetMapping(value = "/{id}/html", produces = MediaType.TEXT_HTML_VALUE)
    public ResponseEntity<String> html(@PathVariable Long id) {
        return ResponseEntity.ok().contentType(MediaType.TEXT_HTML).body("<html/>");
    }
}
"""

OPENAPI = """openapi: 3.1.0
info:
  title: fixture
  version: 1.0.0
paths:
  /api/v1/syn:
    get:
      operationId: SYN-01
      responses:
        200:
          description: 成功
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Envelope"
  /api/v1/syn/{id}/html:
    get:
      operationId: SYN-02
      responses:
        200:
          description: 成功
          content:
            text/html:
              schema:
                type: string
components:
  schemas:
    Envelope:
      type: object
"""

HTTP_TS = """export function http<T = unknown>(path: string, options: RequestOptions = {}): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    uni.request({
      success: (res) => {
        const status = (res as { statusCode?: number }).statusCode ?? 0
        if (status === 401) {
          clearToken()
          reject(new ApiError('E-1902'))
          return
        }
        if (status >= 400) {
          reject(new ApiError(body?.code || 'E-2001'))
          return
        }
        if (!body || typeof body.code !== 'string') {
          reject(new ApiError('E-2001', '响应格式非法'))
          return
        }
        if (body.code !== '0') {
          reject(new ApiError(body.code, body.message))
          return
        }
        resolve(body.data)
      }
    })
  })
}
"""

CLIENT_API = """import { http } from './http'

export const synApi = {
  list() {
    return http<unknown>('/syn', { method: 'GET' })
  }
}
"""

CLIENT_API_WITH_HTML = CLIENT_API + """
export const synHtmlApi = {
  html(id: string) {
    return http<unknown>(`/syn/${encodeURIComponent(id)}/html`, { method: 'GET' })
  }
}
"""

TEST_JAVA = """package syn;

class SynTest {
    void ok() {
        assertThat(res.statusCode()).isEqualTo(200);
        assertThat(res2.status()).isEqualTo(200);
    }
}
"""

EP_JSON = ('{"total": 2, "endpoints": ['
           '{"id": "SYN-01", "method": "GET", "path": "/api/v1/syn", "response_model": "syn-list", "query_params": ["page"], "error_codes": []},'
           '{"id": "SYN-02", "method": "GET", "path": "/api/v1/syn/{id}/html", "response_model": null, "query_params": [], "error_codes": ["E-1401"]}'
           ']}')

GEN_PY = """def _enveloped(model):
    return {"$ref": "#/components/schemas/Envelope"}


for e in PATHS:
    op["responses"] = {
        "200": {
            "description": "成功",
            "content": {"application/json": {"schema": _enveloped(res)}},
        }
    }
"""


def build(root: Path, html_client=False):
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    (root / "docs/backend").mkdir(parents=True)
    (root / "tools").mkdir(parents=True)
    (root / "aap-server/src/main/java/syn").mkdir(parents=True)
    (root / "aap-server/src/test/java/syn").mkdir(parents=True)
    (root / "aap-client/src/api").mkdir(parents=True)

    w = lambda p, t: (root / p).write_text(t, encoding="utf-8", newline="\n")
    w("docs/backend/02-API接口模型清单.md", MD)
    w("docs/backend/endpoints.json", EP_JSON)
    w("docs/backend/openapi.yaml", OPENAPI)
    w("tools/gen-backend-models.py", GEN_PY)
    w("aap-server/src/main/java/syn/SynController.java", CONTROLLER_JSON)
    w("aap-server/src/main/java/syn/SynHtmlController.java", CONTROLLER_HTML)
    w("aap-server/src/test/java/syn/SynTest.java", TEST_JAVA)
    w("aap-client/src/api/http.ts", HTTP_TS)
    w("aap-client/src/api/syn.ts", CLIENT_API_WITH_HTML if html_client else CLIENT_API)


def run(root):
    p = subprocess.run([sys.executable, str(SCRIPT), str(root)], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def fails(out):
    return sorted({line.split()[1] for line in out.splitlines()
                   if re.match(r"^\[FAIL\]\s", line) and len(line.split()) > 1})


def snapshot(root):
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = hashlib.md5(p.read_bytes()).hexdigest()
    return out


MISS = []


def mutate(path, old, new):
    """替换并返回未命中锚点列表（空 = 注入真的改到了源码，坑 66/94）。"""
    txt = path.read_text(encoding="utf-8")
    if old not in txt:
        MISS.append("%s: anchor not found: %s" % (path.name, old[:50]))
        return
    if old == new:
        MISS.append("%s: new == old（注入未改变语义，坑 90）" % path.name)
        return
    path.write_text(txt.replace(old, new), encoding="utf-8", newline="\n")


results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print("[%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


# ---------------- 1. 合规夹具 ----------------
build(FIX / "compliant")
before = snapshot(FIX / "compliant")
rc_ok, ok_out = run(FIX / "compliant")
after = snapshot(FIX / "compliant")
ok_fails = fails(ok_out)
check("T1 合规夹具 rc=0", rc_ok == 0, "rc=%d fails=%s" % (rc_ok, ok_fails))
check("T2 合规夹具 FAIL 0", ok_fails == [], str(ok_fails))
check("T3 正向对照齐全（A0a/A0b/A0c/A0d/A0e/A0f/A1a/A1b/A1c/A2a/A3a/A4a/A5a/A6a/A7a1/A7d 全 PASS）",
      all(("[PASS] %s" % t) in ok_out for t in
          ("A0a", "A0b", "A0c", "A0d", "A0e", "A0f", "A1a", "A1b", "A1c", "A2a", "A3a", "A4a", "A5a", "A6a", "A7a1", "A7d")),
      "")
check("T4 夹具目录零写副作用", before == after,
      "changed=%d" % len([k for k in set(before) | set(after) if before.get(k) != after.get(k)]))
check("T5 合规夹具解析到 2 条端点 / 90 类计数（A0a 计数 = 2）",
      "[PASS] A0a md 逐端点表解析到 2 条" in ok_out, "")

# ---------------- 2. 空夹具 ----------------
build(FIX / "empty")
for p in sorted((FIX / "empty").rglob("*"), reverse=True):
    if p.is_file():
        p.unlink()
rc_e, out_e = run(FIX / "empty")
check("T6 空夹具 rc!=0", rc_e != 0, "rc=%d" % rc_e)
check("T7 空夹具点名 A0a（解析器失效必须转红）", "A0a" in fails(out_e), str(fails(out_e)))

# ---------------- 3. 注入1：openapi 把 html 端点声明成 json → A2b ----------------
build(FIX / "inj1")
mutate(FIX / "inj1/docs/backend/openapi.yaml",
       "          content:\n            text/html:\n              schema:\n                type: string",
       "          content:\n            application/json:\n              schema:\n                $ref: \"#/components/schemas/Envelope\"")
rc1, out1 = run(FIX / "inj1")
new1 = sorted(set(fails(out1)) - set(ok_fails))
check("T8 注入1 后 FAIL 集合恰好新增 {A2b}", new1 == ["A2b"], "new=%s" % new1)

# ---------------- 4. 注入2：实现 produces 改 JSON（openapi 不变）→ {A2b, A3a} ----------------
build(FIX / "inj2")
mutate(FIX / "inj2/aap-server/src/main/java/syn/SynHtmlController.java",
       '@GetMapping(value = "/{id}/html", produces = MediaType.TEXT_HTML_VALUE)',
       '@GetMapping(value = "/{id}/html", produces = MediaType.APPLICATION_JSON_VALUE)')
rc2, out2 = run(FIX / "inj2")
new2 = sorted(set(fails(out2)) - set(ok_fails))
check("T9 注入2 后 FAIL 集合恰好新增 {A2b, A3a}（md↔实现 非包络维度有判别力）",
      new2 == ["A2b", "A3a"], "new=%s" % new2)

# ---------------- 5. 注入3：成功路径非 200 → A1c ----------------
build(FIX / "inj3")
mutate(FIX / "inj3/aap-server/src/main/java/syn/SynController.java",
       "    @GetMapping\n    public ApiEnvelope<Object> list() {",
       "    @GetMapping\n    @ResponseStatus(HttpStatus.CREATED)\n    public ApiEnvelope<Object> list() {")
rc3, out3 = run(FIX / "inj3")
new3 = sorted(set(fails(out3)) - set(ok_fails))
check("T10 注入3 后 FAIL 集合恰好新增 {A1c}（成功非 200 维度有判别力）", new3 == ["A1c"], "new=%s" % new3)

# ---------------- 6. 注入4：客户端消费非包络端点 → A4a ----------------
build(FIX / "inj4", html_client=True)
rc4, out4 = run(FIX / "inj4")
new4 = sorted(set(fails(out4)) - set(ok_fails))
check("T11 注入4 后 FAIL 集合恰好新增 {A4a}（客户端消费维度有判别力）", new4 == ["A4a"], "new=%s" % new4)

# ---------------- 7. 注入5：md 成功行改 201 → A6b ----------------
build(FIX / "inj5")
mutate(FIX / "inj5/docs/backend/02-API接口模型清单.md",
       "| `0` | 200 | 成功 | |", "| `0` | 201 | 成功 | |")
rc5, out5 = run(FIX / "inj5")
new5 = sorted(set(fails(out5)) - set(ok_fails))
check("T12 注入5 后 FAIL 集合恰好新增 {A6b}（md↔openapi 成功状态维度有判别力）", new5 == ["A6b"], "new=%s" % new5)

# ---------------- 8. 注入必须真的改到源码 ----------------
check("T13 全部注入锚点命中（未命中/未改变语义 = 空转通过，坑 66/90/94）", MISS == [], str(MISS))

# ---------------- 9. 真实仓库只读守卫 ----------------
g0 = subprocess.run(["git", "-C", str(REAL), "status", "--porcelain"], capture_output=True, text=True).stdout
rcr, outr = run(REAL)
g1 = subprocess.run(["git", "-C", str(REAL), "status", "--porcelain"], capture_output=True, text=True).stdout
check("T14 真实仓库只读（git status 不变）", g0 == g1, "")
check("T15 真实仓库 FAIL 集合恰好 = {A2b}（RPT-03 生成物侧漂移）", fails(outr) == ["A2b"], str(fails(outr)))
check("T16 真实仓库正向对照：控制器定位 90/90 且解析到 90 个 operation",
      "[PASS] A0c 控制器路由定位到清单端点 90/90" in outr and "解析到 90 个 operation" in outr, "rc=%d" % rcr)

print()
bad_total = [n for n, okk, _ in results if not okk]
print("自测汇总：%d/%d PASS" % (len(results) - len(bad_total), len(results)))
if bad_total:
    print("失败用例：%s" % ", ".join(bad_total))
sys.exit(1 if bad_total else 0)
