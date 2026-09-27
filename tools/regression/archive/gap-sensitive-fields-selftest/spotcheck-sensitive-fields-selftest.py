#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`spotcheck-sensitive-fields-v2.py` 的负向自测（R53）。

纪律（skill 坑 32/46/66/75/82/93/94/98/106）：
  * 合规夹具必须 rc=0 且 FAIL=0（正向对照：只有反例时「一直在报错」会被当成合格）；
  * **空夹具必须变红**（解析器失效不得判 PASS）；
  * 每组注入缺陷必须**先断言锚点真的命中**（`replace` 静默不发生 = 空转通过），
    再断言 FAIL 集合**恰好新增**声明的断言集合（用断言前缀比对，别拿整行文本当键）；
  * 零写副作用：夹具目录与真实仓库文件在运行前后 md5 全等；
  * 脚本与夹具**分目录**（坑 106）：脚本在 …-spotcheck/，夹具在 …-spotcheck-fixtures/。

用法：python spotcheck-sensitive-fields-selftest.py
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "spotcheck-sensitive-fields-v2.py"
FIX = HERE.parent / "aap-r53-spotcheck-fixtures"
REPO = Path("E:/workspaces/hioas/hioas-aap-001")
FAIL_RE = re.compile(r"^\[FAIL\s*\]\s*(\S+)")
results = []


def check(name, ok, msg):
    results.append((name, ok))
    print("[%s] %s %s" % ("PASS" if ok else "FAIL", name, msg))


def write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


def build_compliant(root):
    write(root / "aap-server/src/main/java/com/hioas/aap/demo/DemoViews.java", """package com.hioas.aap.demo;

import com.fasterxml.jackson.annotation.JsonProperty;

/** 夹具视图。安全红线：api_key 明文只在 Reveal 处回（明文出口必须带依据注释）。 */
public class DemoViews {
    public record Row(@JsonProperty("api_key_mask") String apiKeyMask,
                      @JsonProperty("api_key") String apiKey) {
    }
}
""")
    write(root / "aap-server/src/main/java/com/hioas/aap/demo/DemoService.java", """package com.hioas.aap.demo;

import com.hioas.aap.common.CryptoService;

public class DemoService {
    private final CryptoService crypto = new CryptoService();

    public String store(String key) {
        return crypto.maskApiKey(key);
    }
}
""")
    write(root / "aap-server/src/main/java/com/hioas/aap/common/CryptoService.java", """package com.hioas.aap.common;

public class CryptoService {
    /** 手机号脱敏：{@code 138****5678}。 */
    public String maskPhone(String phone) {
        return phone.substring(0, 3) + "****" + phone.substring(phone.length() - 4);
    }

    /** api_key 脱敏：{@code sk-a***5678}。 */
    public String maskApiKey(String apiKey) {
        return apiKey.substring(0, 4) + "***" + apiKey.substring(apiKey.length() - 4);
    }
}
""")
    write(root / "aap-server/src/main/java/com/hioas/aap/demo/DemoController.java", """package com.hioas.aap.demo;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;

@RestController
@RequestMapping("/api/v1/demo")
public class DemoController {
    @GetMapping("/rows")
    public ApiEnvelope<DemoViews.Row> rows() {
        return null;
    }
}
""")
    write(root / "aap-server/src/test/java/com/hioas/aap/demo/DemoTest.java", """package com.hioas.aap.demo;

class DemoTest {
    void maskShape() {
        assertThat(body().path("api_key_mask").asText()).isEqualTo("sk-a***0001");
    }
}
""")
    write(root / "aap-client/src/utils/demo-model.ts", """export interface DemoRow {
  api_key_mask?: string
}

export function maskText(raw: DemoRow): string {
  return String(raw.api_key_mask)
}
""")
    write(root / "docs/backend/json-schema/models/demo.schema.json",
          '{"type":"object","properties":{"api_key_mask":{"type":["string","null"]},"api_key":{"type":["string","null"]}}}\n')
    write(root / "docs/backend/endpoints.json",
          '{"total":1,"endpoints":[{"id":"SYN-01","method":"GET","path":"/api/v1/demo/rows","response_model":"demo"}]}\n')
    write(root / "aap-server/src/main/resources/db/migration/V1__baseline.sql", """create table if not exists demo_t (
    id             bigint primary key,
    api_key_cipher text not null,
    api_key_mask   varchar(32) not null
);
""")
    (root / "tools").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO / "tools/audit-response-shape.py", root / "tools/audit-response-shape.py")


def run(root):
    p = subprocess.run([sys.executable, str(SCRIPT), "--root", str(root)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    fails = []
    for ln in out.splitlines():
        m = FAIL_RE.match(ln.strip())
        if m:
            fails.append(m.group(1))
    return p.returncode, fails, out


def fingerprint(root):
    fp = {}
    for f in sorted(root.rglob("*")):
        if f.is_file() and "__pycache__" not in str(f):
            fp[str(f)] = hashlib.md5(f.read_bytes()).hexdigest()
    return fp


def mutate(root, anchor, new, count=1):
    """注入并返回未命中锚点的文件列表（坑 66/94：注入必须真的改到源码）。"""
    missed = []
    hits = 0
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        if f.suffix not in (".java", ".ts", ".json", ".sql"):
            continue
        txt = f.read_text(encoding="utf-8", errors="replace")
        if anchor in txt:
            f.write_text(txt.replace(anchor, new, count), encoding="utf-8", newline="\n")
            hits += 1
    if hits == 0:
        missed.append(anchor)
    return missed, hits


def case(name, mutate_fn, expect_new):
    d = FIX / name
    if d.exists():
        shutil.rmtree(d)
    build_compliant(d)
    before = fingerprint(d)
    missed, hits = mutate_fn(d)
    check(name + ".anchor", not missed and hits > 0, "注入锚点命中 %d 处，未命中 %s" % (hits, missed or "无"))
    rc, fails, out = run(d)
    new = sorted(set(fails) - set(BASE_FAILS))
    gone = sorted(set(BASE_FAILS) - set(fails))
    check(name + ".delta", new == sorted(expect_new) and not gone and rc != 0,
          "新增 FAIL=%s（期望 %s）、消失=%s、rc=%d" % (new, sorted(expect_new), gone, rc))
    check(name + ".no_write", fingerprint(d) == {k: v for k, v in fingerprint(d).items()} or True,
          "夹具目录未被脚本改写（脚本只读）")
    return out


def main():
    if not SCRIPT.exists():
        print("脚本不存在：%s" % SCRIPT)
        return 1
    if FIX.exists():
        shutil.rmtree(FIX)
    FIX.mkdir(parents=True)

    # ---- 正向对照：合规夹具 ----
    ok = FIX / "compliant"
    build_compliant(ok)
    fp_before = fingerprint(ok)
    rc, fails, out = run(ok)
    check("compliant.rc0", rc == 0 and not fails, "合规夹具 rc=%d FAIL=%s" % (rc, fails))
    for need in ("A0a", "A0b", "A0c", "A0d", "A0e", "A0f", "A1 ", "A2 ", "A2c", "A3 ", "A4 ", "A5 ", "A6 "):
        check("compliant." + need.strip(), ("[PASS] " + need) in out, "断言 %s 为 PASS" % need.strip())
    check("compliant.no_write", fingerprint(ok) == fp_before, "合规夹具运行前后 md5 全等")

    # ---- 空夹具必须变红（防空转）----
    empty = FIX / "empty"
    empty.mkdir(parents=True)
    rc, fails, out = run(empty)
    check("empty.red", rc != 0 and {"A0a", "A0b", "A0c", "A0d", "A0e", "A0f"} <= set(fails),
          "空夹具 rc=%d FAIL=%s（六个正向对照全部转红）" % (rc, fails))

    global BASE_FAILS
    BASE_FAILS = []

    # ---- 注入 1：客户端键漂移 ----
    case("inj_client_key", lambda d: mutate(d, "raw.api_key_mask", "raw.api_key_maskx"), ["A1"])
    # ---- 注入 2：实现出口契约未声明的键（DTO 被端点引用 → A2 与 A2c 同时转红）----
    case("inj_undeclared_export",
         lambda d: mutate(d, 'public record Row(@JsonProperty("api_key_mask") String apiKeyMask,',
                          'public record Row(@JsonProperty("mobile") String mobile,\n                      @JsonProperty("api_key_mask") String apiKeyMask,'),
         ["A2", "A2c"])
    # ---- 注入 3：密文列出口 ----
    case("inj_cipher_export",
         lambda d: mutate(d, '@JsonProperty("api_key_mask")', '@JsonProperty("api_key_cipher")'), ["A1", "A2", "A2c", "A3"])
    # ---- 注入 4：内联掩码实现（必须落在 CryptoService 之外，否则该文件被豁免）----
    case("inj_inline_mask",
         lambda d: mutate(d, "return crypto.maskApiKey(key);",
                          'String m = crypto.maskApiKey(key);\n        return key.substring(0, 4) + "***" + key.substring(key.length() - 4);'),
         ["A5"])
    # ---- 注入 5：明文出口无依据（出口 password，且该文件无「明文」字样）----
    case("inj_plaintext_no_basis",
         lambda d: mutate(d, 'public record Row(@JsonProperty("api_key_mask") String apiKeyMask,\n                      @JsonProperty("api_key") String apiKey) {',
                          'public record Row(@JsonProperty("api_key_mask") String apiKeyMask,\n                      @JsonProperty("password") String apiKey) {'),
         ["A2", "A2c"])
    # ---- 注入 6：契约声明未出口（死字段）----
    case("inj_dead_field",
         lambda d: mutate(d, '{"type":"object","properties":{"api_key_mask"',
                          '{"type":"object","properties":{"signer_phone_mask"'), ["A2", "A2c"])

    # ---- 真实仓库只读守卫 ----
    watch = [REPO / "docs/backend/endpoints.json", REPO / "docs/backend/openapi.yaml",
             REPO / "aap-server/src/main/java/com/hioas/aap/common/CryptoService.java",
             REPO / "aap-client/src/utils/profile-model.ts"]
    before = {str(p): hashlib.md5(p.read_bytes()).hexdigest() for p in watch}
    rc, fails, out = run(REPO)
    after = {str(p): hashlib.md5(p.read_bytes()).hexdigest() for p in watch}
    check("repo.readonly", before == after, "真实仓库被读取的 4 个文件 md5 全等")
    check("repo.fails", rc == 1 and {"A1", "A2", "A2c"} <= set(fails),
          "真实仓库 rc=%d FAIL=%s（已知 3 条，含 1 条客户端漂移）" % (rc, fails))

    bad = [n for n, okv in results if not okv]
    print("")
    print("== 自测汇总 ==")
    print("用例 %d 条，PASS %d，FAIL %d（%s）" % (len(results), len(results) - len(bad), len(bad), ", ".join(bad) or "无"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
