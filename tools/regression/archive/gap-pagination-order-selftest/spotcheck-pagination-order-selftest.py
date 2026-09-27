#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R45 抽查脚本的判别力自测（skill 坑 46/57/66/75/82/90/93）。

用例：
  case_positive      合规夹具（= 真实仓库拷贝）rc=1 且 FAIL 集合 = 基线（1 条 usage）
  case_inject_impl   注入「去掉一条 SQL 的 id tie-breaker」-> 恰好新增 1 条点名 NotificationService
  case_inject_ddl    注入「删掉 aap_notification 的 inline primary key」-> 恰好新增 1 条点名 NotificationService
  case_fix_usage     注入「给 usage 补上 channel_id」-> 基线那 1 条 FAIL **消失**（证明守卫不是永远报错）
  case_empty         空夹具必须变红且点名 P0/P0b（解析器失效判 9，不等于零发现）
  case_zero_write    真实仓库三个被读文件 md5 全等（零写副作用）
  anchors            所有注入锚点必须真的改到源码（坑 66/94：锚点失效 = 空转通过）

用法： python spotcheck-pagination-order-selftest.py
退出码：0 = 全部用例通过
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "spotcheck-pagination-order-v2.py")
REPO = "E:/workspaces/hioas/hioas-aap-001"
TMP = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Temp")
FIX = os.path.join(TMP, "aap-r45-fixture")
RESULTS = []
UNHIT = []

SUBTREES = [
    ("aap-server/src/main/java", True),
    ("aap-server/src/main/resources/db/migration", True),
    ("aap-server/src/test/java", True),
    ("aap-client/src", True),
    ("docs/backend", True),
]


def emit(ok, name, detail=""):
    tag = "PASS" if ok else "FAIL"
    RESULTS.append((tag, name))
    print("[%s] %s%s" % (tag, name, ("：" + detail) if detail else ""))


def build_fixture(dest):
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    for sub, _ in SUBTREES:
        src = os.path.join(REPO, sub.replace("/", os.sep))
        dst = os.path.join(dest, sub.replace("/", os.sep))
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "w").close()
    # 只保留 V1__baseline.sql 之外的迁移不影响判定，但为真实性全量拷贝
    return dest


def run(fixture):
    p = subprocess.run([sys.executable, SCRIPT, "--repo", fixture],
                       capture_output=True, text=True)
    return p.returncode, p.stdout


def fails_of(out):
    """FAIL 断言行（按断言前缀 + 定位串比对；坑 82/93）"""
    return sorted({re.sub(r'^\[FAIL\s*\]\s*', '', l).strip()
                   for l in out.splitlines() if re.match(r'^\[FAIL\s*\]', l)})


def detail_fails(out):
    """只取「明细」FAIL 行 —— 汇总行的数字天然会变，混进来会把「新增 1 条」误判成 2 条（坑 59 同族）。"""
    return [x for x in fails_of(out) if "汇总" not in x]


def mutate(path, pairs):
    """返回未命中锚点列表（坑 66：注入必须真的改到源码）"""
    with open(path, encoding="utf-8") as fh:
        txt = fh.read()
    missed = []
    for old, new in pairs:
        if old not in txt:
            missed.append(old[:60])
            continue
        txt = txt.replace(old, new)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(txt)
    return missed


def main():
    fixture = build_fixture(FIX)
    notif = os.path.join(fixture, "aap-server/src/main/java/com/hioas/aap/support/NotificationService.java")
    usage = os.path.join(fixture, "aap-server/src/main/java/com/hioas/aap/usage/UsageService.java")
    ddl = os.path.join(fixture, "aap-server/src/main/resources/db/migration/V1__baseline.sql")

    # ---- case_positive（基线）
    ok_out = run(fixture)
    base_fails = detail_fails(ok_out[1])
    emit(ok_out[0] == 1, "case_positive 合规夹具 rc=1（真实仓库本有 1 条待拍板 FAIL）", "rc=%d" % ok_out[0])
    emit(len(base_fails) == 1, "case_positive 基线 FAIL 明细行数 = 1（usage 分页缺 channel_id）",
         "实得 %d：%s" % (len(base_fails), base_fails))
    emit(any("UsageService.java:167" in f for f in base_fails),
         "case_positive 基线点名 UsageService.java:167（usage 分页缺 channel_id）")

    # ---- case_inject_impl：去掉 NotificationService 分页 SQL 的 id tie-breaker
    missed = mutate(notif, [("order by created_at desc, id desc limit ? offset ?",
                             "order by created_at desc limit ? offset ?")])
    UNHIT.extend(missed)
    out = run(fixture)
    f = detail_fails(out[1])
    new = [x for x in f if x not in base_fails]
    emit(out[0] == 1 and len(new) == 1 and "NotificationService" in new[0],
         "case_inject_impl 注入实现缺陷 -> 恰好新增 1 条点名 NotificationService 的 FAIL",
         "新增 %d 条：%s" % (len(new), new[:1]))
    build_fixture(FIX)  # 还原

    # ---- case_inject_ddl：删掉 aap_notification 的 inline primary key
    with open(ddl, encoding="utf-8") as fh:
        ddl_txt = fh.read()
    m = re.search(r'create table if not exists aap_notification \(([\s\S]*?)\n\);', ddl_txt, re.I)
    anchor = None
    if m:
        blk = m.group(1)
        am = re.search(r'^(\s*id\s+bigint\s+)primary key\b', blk, re.M | re.I)
        if am:
            anchor = am.group(0)
    if anchor is None:
        UNHIT.append("aap_notification id primary key")
        emit(False, "case_inject_ddl 锚点未找到（aap_notification 的 id primary key）")
    else:
        # 只在 aap_notification 的表块内替换 —— 同一缩进的 `id bigint primary key` 在别的表里也有，
        # 全文件 replace 会一次打掉 8 张表的唯一键（首版真实返工，坑 90/94：注入必须精确且语义真的变）
        patched = ddl_txt[:m.start(1)] + blk.replace(anchor, anchor.replace("primary key", "not null"), 1) \
            + ddl_txt[m.end(1):]
        with open(ddl, "w", encoding="utf-8") as fh:
            fh.write(patched)
        if anchor.replace("primary key", "not null") not in patched:
            UNHIT.append("ddl-scoped-injection")
        out = run(fixture)
        f = detail_fails(out[1])
        new = [x for x in f if x not in base_fails]
        emit(out[0] == 1 and len(new) == 1 and "NotificationService" in new[0],
             "case_inject_ddl 删掉该表唯一键 -> 恰好新增 1 条点名 NotificationService 的 FAIL",
             "新增 %d 条：%s" % (len(new), new[:1]))
        build_fixture(FIX)

    # ---- case_fix_usage：补上 channel_id（基线 FAIL 必须消失，证明守卫有判别力而非恒报错）
    missed = mutate(usage, [("order by stat_hour, model_name, group_name\"",
                             "order by stat_hour, model_name, group_name, channel_id\"")])
    UNHIT.extend(missed)
    out = run(fixture)
    f = detail_fails(out[1])
    gone = [x for x in base_fails if x not in f]
    emit(out[0] == 0 and not f and len(gone) == 1,
         "case_fix_usage 补 channel_id -> 基线 FAIL 全部消失、rc=0（守卫不恒报错）",
         "rc=%d 剩余 FAIL=%d 消失=%d" % (out[0], len(f), len(gone)))

    # ---- case_empty：空夹具
    empty = os.path.join(TMP, "aap-r45-fixture-empty")
    build_fixture(empty)
    for sub, _ in SUBTREES:
        p = os.path.join(empty, sub.replace("/", os.sep))
        if os.path.isdir(p):
            shutil.rmtree(p)
        os.makedirs(p, exist_ok=True)
    for f2 in ("aap-server/src/main/resources/db/migration/V1__baseline.sql",
               "docs/backend/02-API接口模型清单.md", "docs/backend/openapi.yaml"):
        p = os.path.join(empty, f2.replace("/", os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").close()
    out = run(empty)
    f = fails_of(out[1])
    emit(out[0] == 9 and any("P0 " in x for x in f) and any("P0b" in x for x in f),
         "case_empty 空夹具 rc=9（解析器失效）且点名 P0/P0b，不判「零发现」",
         "rc=%d FAIL=%s" % (out[0], f))

    # ---- 锚点
    emit(not UNHIT, "anchors 所有注入锚点都真的改到了源码（坑 66/94）", "未命中=%s" % UNHIT)

    # ---- 零写副作用（真实仓库）
    md5 = {}
    for p in ("aap-server/src/main/java/com/hioas/aap/usage/UsageService.java",
              "aap-server/src/main/java/com/hioas/aap/support/NotificationService.java",
              "aap-server/src/main/resources/db/migration/V1__baseline.sql"):
        md5[p] = hashlib.md5(open(os.path.join(REPO, p.replace("/", os.sep)), "rb").read()).hexdigest()
    after = {p: hashlib.md5(open(os.path.join(REPO, p.replace("/", os.sep)), "rb").read()).hexdigest()
             for p in md5}
    emit(md5 == after, "case_zero_write 真实仓库 3 个关键文件 md5 全等（自测零写副作用）")

    n_fail = sum(1 for t, _ in RESULTS if t == "FAIL")
    print("\n== 自测结果：PASS %d / FAIL %d ==" % (len(RESULTS) - n_fail, n_fail))
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
