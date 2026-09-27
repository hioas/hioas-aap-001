"""R51 抽查脚本负向自测（判别力实测）。

纪律（每条都是本项目踩过的坑）：
  - 夹具目录与脚本目录**分开命名**（坑 106）
  - 注入缺陷前先断言**锚点全部命中**（坑 66/94）；注入后断言**新文本真的出现**
  - FAIL 集合按**断言前缀**比对（坑 82/93），基线用专用变量名 ok_out（坑 93）
  - forbid 断言带 `[FAIL] ` 前缀（坑 77）
  - 每个源都有正向对照（> 0），空夹具必须点名 A0x（坑 46/75）
  - 真实仓库运行零写副作用（坑 39/40）
  - 注入值不与旧值有子串包含关系（坑 90/94）
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aap-r51-status-machine.py")
FIX = r"C:/Users/laitz/AppData/Local/Temp/aap-r51-spotcheck-fixtures"
ROOT = r"E:/workspaces/hioas/hioas-aap-001"
FAIL_RE = re.compile(r"\[FAIL\s*\]")

PASS = []
FAIL = []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print("%s %s%s" % ("[PASS]" if cond else "[FAIL]", name, (" :: " + detail) if detail else ""))


MD = """# 夹具清单
| ID | 方法 | 路径 | 认证 | 请求 | 响应 | 错误码 | 备注 | 来源 | 任务号 |
|---|---|---|---|---|---|---|---|---|---|
| SYN-01 | POST | `/syn/things/{id}/publish` | \u2705 | \u2014 | `Thing`\uff08DRAFT\u2192PUBLISHED\uff09 | E-1601 | | \u771f\u6e90 | T01 |
| SYN-02 | POST | `/syn/things/{id}/cancel` | \u2705 | \u2014 | `Thing` | E-1601 E-1305 | | \u63a8\u65ad | T01 |
"""

ER = """# 夹具 ER
**aap_thing**
| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | bigint | PK | |
| status | varchar(32) | IDX | `DRAFT/PUBLISHED/SUPERSEDED/CANCELLED` |

**aap_other**：`id bigint`、`status`(NEW/DONE)\u3002
"""

DDL = """create table aap_thing (
    id bigint primary key,
    status varchar(32) not null default 'DRAFT',
    deleted boolean not null default false
);
create table aap_other (
    id bigint primary key,
    status varchar(32) not null default 'NEW'
);
"""

ENTITY = """package com.hioas.aap.thing;

import com.mybatisflex.annotation.Table;

@Table("aap_thing")
public class ThingEntity {
    private String status;
    public String getStatus() { return status; }
    public void setStatus(String v) { this.status = v; }
}
"""

SERVICE = """package com.hioas.aap.thing;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import org.springframework.jdbc.core.JdbcTemplate;

public class ThingService {
    private final JdbcTemplate jdbc;
    private final ThingMapper thingMapper;

    public ThingService(JdbcTemplate jdbc, ThingMapper thingMapper) {
        this.jdbc = jdbc;
        this.thingMapper = thingMapper;
    }

    /** SYN-01 发布：DRAFT -> PUBLISHED（条件 UPDATE）。 */
    public void publish(Long id) {
        int affected = jdbc.update(\"\"\"
                update aap_thing
                   set status = 'PUBLISHED', updated_at = now()
                 where id = ? and status = 'DRAFT' and deleted = false
                \"\"\", id);
        if (affected != 1) {
            throw new ApiException(ErrorCode.E_1601, "状态非法");
        }
    }

    /** SYN-02 取消：写入 CANCELLED（ORM setter）。 */
    public void cancel(Long id) {
        ThingEntity entity = thingMapper.selectOneById(id);
        if ("CANCELLED".equals(entity.getStatus())) {
            throw new ApiException(ErrorCode.E_1305, "任务不可取消");
        }
        entity.setStatus("CANCELLED");
        thingMapper.update(entity);
    }

    /** 旧活版置 SUPERSEDED（ORM setter）。 */
    public void supersede(Long id) {
        ThingEntity entity = thingMapper.selectOneById(id);
        entity.setStatus("SUPERSEDED");
        thingMapper.update(entity);
    }
}
"""

MAPPER = """package com.hioas.aap.thing;

public interface ThingMapper {
    ThingEntity selectOneById(Long id);
    int update(ThingEntity entity);
}
"""

SCHEMA = """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "thing",
  "required": ["id", "status"],
  "properties": {
    "id": {"type": ["string", "null"]},
    "status": {"type": ["string", "null"], "enum": ["DRAFT", "PUBLISHED", "SUPERSEDED", "CANCELLED"]}
  }
}
"""

GEN = '''PATHS = []

STATUS = {
    "ThingStatus": ["DRAFT", "PUBLISHED", "SUPERSEDED", "CANCELLED"],
}
'''


def write(root, rel, content):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    return p


def build(root, overrides=None):
    overrides = overrides or {}
    files = {
        "docs/backend/02-API接口模型清单.md": MD,
        "docs/backend/01-ER数据模型.md": ER,
        "docs/backend/json-schema/models/thing.schema.json": SCHEMA,
        "aap-server/src/main/resources/db/migration/V1__baseline.sql": DDL,
        "aap-server/src/main/java/com/hioas/aap/thing/ThingEntity.java": ENTITY,
        "aap-server/src/main/java/com/hioas/aap/thing/ThingService.java": SERVICE,
        "aap-server/src/main/java/com/hioas/aap/thing/ThingMapper.java": MAPPER,
        "tools/gen-backend-models.py": GEN,
    }
    files.update(overrides)
    for rel, content in files.items():
        write(root, rel, content)


def mutate(root, rel, old, new, count=1):
    """注入缺陷：返回未命中的锚点（空 = 全部命中）。"""
    p = os.path.join(root, rel)
    with open(p, encoding="utf-8") as fh:
        txt = fh.read()
    if old not in txt:
        return [old]
    n = txt.count(old)
    if count == -1:
        out = txt.replace(old, new)
    else:
        out = txt.replace(old, new, count)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(out)
    return [] if out != txt else [old]


def run(root):
    p = subprocess.run([sys.executable, SCRIPT, "--root", root], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def fails(out):
    """FAIL 明细行（排除汇总行，坑 103）→ 断言 token 集合。"""
    toks = []
    for ln in out.splitlines():
        s = ln.strip()
        if not FAIL_RE.match(s) or "汇总" in s:
            continue
        body = s[s.index("]") + 1:].strip()
        toks.append(body.split()[0] if body else "?")
    return toks


def raw_fails(out):
    return [ln.strip() for ln in out.splitlines() if FAIL_RE.match(ln.strip()) and "汇总" not in ln]


def tok(line):
    """明细行的断言名（精确匹配，避免 'A1' 前缀误配 'A1b'/'A1bg'，坑 82）。"""
    body = line[line.index("]") + 1:].strip()
    return body.split()[0] if body else "?"


def main():
    if os.path.isdir(FIX):
        for fn in os.listdir(FIX):
            p = os.path.join(FIX, fn)
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
    os.makedirs(FIX, exist_ok=True)

    # ============ 0. 真实仓库只读守卫（零写副作用）
    def fp():
        out = {}
        for base in ("docs/backend", "aap-server/src/main/java", "tools"):
            for dp, _dn, fns in os.walk(os.path.join(ROOT, base)):
                for fn in fns:
                    p = os.path.join(dp, fn)
                    out[p] = hashlib.md5(open(p, "rb").read()).hexdigest()
        return out

    before = fp()
    rc_real, out_real = run(ROOT)
    after = fp()
    check("R0 真实仓库零写副作用", before == after,
          "changed=%d" % len([k for k in before if before.get(k) != after.get(k)]))
    check("R1 真实仓库 FAIL 行数 > 0（正向对照）", len(raw_fails(out_real)) > 0,
          "FAIL=%d" % len(raw_fails(out_real)))
    real_has_A1 = any(t.startswith("A1") for t in fails(out_real))
    check("R2 真实仓库 A1 有判定（> 0）", real_has_A1)

    # ============ 1. 合规夹具
    ok_root = os.path.join(FIX, "ok")
    build(ok_root)
    ok_rc, ok_out = run(ok_root)
    check("C1 合规夹具 rc=0", ok_rc == 0, "rc=%d" % ok_rc)
    check("C2 合规夹具 FAIL 数 = 0", len(raw_fails(ok_out)) == 0, str(raw_fails(ok_out))[:200])
    ok_toks = fails(ok_out)
    ok_lines = raw_fails(ok_out)
    # 正向对照要在**输出全文**里找 PASS 行（FAIL token 列表里当然找不到 PASS，坑 46/75）
    check("C3 合规夹具正向对照（输出里有 A0a/A1/A2/A3g/A4g/A7g 的 PASS 行）",
          all(("[PASS] " + t) in ok_out for t in ("A0a", "A1", "A2", "A3g", "A4g", "A7g")))

    # ============ 2. 空夹具必须变红
    empty_root = os.path.join(FIX, "empty")
    os.makedirs(empty_root, exist_ok=True)
    e_rc, e_out = run(empty_root)
    et = fails(e_out)
    check("C4 空夹具 rc=1", e_rc == 1)
    for tag in ("A0a", "A0b", "A0c", "A0d", "A0e"):
        check("C4 空夹具点名 %s" % tag, tag in et, str(et)[:160])
    check("C4 空夹具 A1g/A2g/A3g 不得空转判绿",
          all(t in et for t in ("A1g", "A2g", "A3g")), str(et)[:160])
    # ============ 3..N 注入缺陷（每条：先断言锚点命中 → 再断言 FAIL 集合恰好新增目标断言）
    cases = [
        # (名称, 注入函数, 期望新增断言前缀, 允许新增条数)
        ("I1 ER 域删掉实现写入的状态 CANCELLED → A1",
         lambda r: mutate(r, "docs/backend/01-ER数据模型.md", "DRAFT/PUBLISHED/SUPERSEDED/CANCELLED",
                          "DRAFT/PUBLISHED/SUPERSEDED/ARCHIVED"), "A1", 1),
        ("I2 生成器枚举删掉 CANCELLED → A1b",
         lambda r: mutate(r, "tools/gen-backend-models.py",
                          '["DRAFT", "PUBLISHED", "SUPERSEDED", "CANCELLED"]',
                          '["DRAFT", "PUBLISHED", "SUPERSEDED", "ARCHIVED"]'), "A1b", 1),
        ("I3 实现写入域外状态 → A1",
         lambda r: mutate(r, "aap-server/src/main/java/com/hioas/aap/thing/ThingService.java",
                          'entity.setStatus("CANCELLED");', 'entity.setStatus("WITHDRAWN");'), "A1", 1),
        ("I4 SQL from 守卫越域 → A2",
         lambda r: mutate(r, "aap-server/src/main/java/com/hioas/aap/thing/ThingService.java",
                          "and status = 'DRAFT' and deleted = false", "and status = 'BOGUS' and deleted = false"),
         "A2", 1),
        ("I5 SQL 删掉 from 守卫 → A5",
         lambda r: mutate(r, "aap-server/src/main/java/com/hioas/aap/thing/ThingService.java",
                          "and status = 'DRAFT' and deleted = false", "and deleted = false"), "A5", 1),
        ("I6 md 声明不存在的迁移 → A3",
         lambda r: mutate(r, "docs/backend/02-API接口模型清单.md", "DRAFT\u2192PUBLISHED", "DRAFT\u2192ARCHIVED"),
         "A3", 1),
        ("I7 md 声明孤儿状态码 → A4",
         lambda r: mutate(r, "docs/backend/02-API接口模型清单.md", "E-1601 E-1305", "E-1601 E-1305 E-1701"),
         "A4", 1),
        ("I8 ER 域加全仓库零出现的状态 → A6",
         lambda r: mutate(r, "docs/backend/01-ER数据模型.md", "DRAFT/PUBLISHED/SUPERSEDED/CANCELLED",
                          "DRAFT/PUBLISHED/SUPERSEDED/CANCELLED/QUARANTINED"), "A6", 1),
        ("I9 schema enum 比 ER 少一个值 → A7",
         lambda r: mutate(r, "docs/backend/json-schema/models/thing.schema.json",
                          '"enum": ["DRAFT", "PUBLISHED", "SUPERSEDED", "CANCELLED"]',
                          '"enum": ["DRAFT", "PUBLISHED"]'), "A7", 1),
    ]

    for (name, fn, want, want_n) in cases:
        r = os.path.join(FIX, re.sub(r"[^A-Za-z0-9]+", "-", name.split()[0]))
        build(r)
        missed = fn(r)
        check("%s :: 锚点全部命中" % name, not missed, "未命中=%s" % missed)
        if missed:
            continue
        rc2, out2 = run(r)
        # 按**明细行**比对（不是 token 集合：同名断言的多条明细会被集合去重吞掉，坑 97/109）
        new_lines = [l for l in raw_fails(out2) if l not in ok_lines]
        hit = [l for l in new_lines if tok(l) == want]
        check("%s :: 恰好新增 %d 条 %s" % (name, want_n, want), len(hit) == want_n,
              "命中=%s（全部新增=%s）" % (hit, new_lines))

    # ============ 正向判别力：switch 的 case 标签不得被当成写入值（坑 64 回归守卫）
    sw_root = os.path.join(FIX, "switch-ok")
    build(sw_root)
    svc = SERVICE.replace(
        '        entity.setStatus("CANCELLED");',
        '        entity.setStatus(switch (flag) {\n'
        '            case "PUBLISHED" -> "CANCELLED";\n'
        '            default -> "DRAFT";\n'
        '        });')
    write(sw_root, "aap-server/src/main/java/com/hioas/aap/thing/ThingService.java", svc)
    sw_rc, sw_out = run(sw_root)
    sw_new = [l for l in raw_fails(sw_out) if l not in ok_lines]
    check("P1 switch case 标签不被当写入值（不新增 FAIL）", not sw_new, "新增=%s" % sw_new)

    # ============ 正向判别力：把未定位的接收者类型补上后 A8 未判定数下降（信息项，不误报 FAIL）
    u_root = os.path.join(FIX, "unresolved")
    build(u_root, {"aap-server/src/main/java/com/hioas/aap/thing/ThingEntity.java":
                   ENTITY.replace('@Table("aap_thing")', '@Table("aap_other")')})
    u_rc, u_out = run(u_root)
    u_new = [l for l in raw_fails(u_out) if l not in ok_lines]
    check("P2 实体映射改到别表 → A1 报越界（CANCELLED 不在 aap_other 域）",
          any(tok(l) == "A1" for l in u_new), "新增=%s" % u_new)

    # ============ 自我断言检查（坑 77/82/93）
    check("S1 forbid 前缀正确（PASS 行不含 FAIL 标记）",
          not any(FAIL_RE.match(l) for l in PASS))
    check("S2 基线变量 ok_lines 未被后续用例覆盖（注入后仍为空）", ok_lines == [],
          "ok_lines=%s" % ok_lines)

    print("")
    print("自测汇总：PASS %d / FAIL %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("失败项：%s" % FAIL)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
