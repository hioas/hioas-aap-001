#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回归面「脚本归仓」：把住在 $TEMP 的抽查脚本**存档进仓库**，并留下可一键还原的映射 + 校验和。

为什么（真实脆弱点，历史 169/177 的终极形态）：R489 的回归面 84 条里有 54 条执行的脚本住在
`$TEMP/aap-rNN-spotcheck/`。系统清理 Temp / 换机 = 整批不变量抽查**永久退场**（R47 已经发生过一次），
而每轮报告都写「既有审计零回归」——缺席无人察觉。

本脚本**只复制、不改写、不执行**被测脚本：
  * 归档到 `tools/regression/archive/<tag>/<原文件名>`，逐字节 sha256 留档；
  * 原文件路径 + sha256 落 `tools/regression/archive/RESTORE.json`，供 `--restore` 一键还原到原位置；
  * `--check` 只读复核：归档 ↔ 原文件逐字节一致（缺原文件时报告「原文件已丢失，可用归档还原」）。

用法：
  python tools/round-verify/archive-temp-scripts.py            # 归仓（幂等：内容一致即跳过）
  python tools/round-verify/archive-temp-scripts.py --check    # 只读复核（不写任何文件）
  python tools/round-verify/archive-temp-scripts.py --restore  # 按 RESTORE.json 还原缺失的原文件
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path("E:/workspaces/hioas/hioas-aap-001")
MANIFEST = ROOT / "tools/round-verify/manifest.json"
ARCH = ROOT / "tools/regression/archive"
INDEX = ARCH / "RESTORE.json"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def entries():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return m["audits"] + m["selftests"]


def load_index():
    if INDEX.exists():
        return json.loads(INDEX.read_text(encoding="utf-8"))
    return {"_note": "回归面 $TEMP 脚本归仓索引：archived → original（绝对路径）。"
                     "原文件丢失时用 --restore 还原，再跑 run-round.sh。",
            "items": {}}


def do_archive():
    idx = load_index()
    items = idx["items"]
    allx = entries()
    external = [x for x in allx if not x["cmd"][1].startswith("tools/")]
    print("回归面 %d 条 → 仓库内脚本 %d 条 / 仓库外（$TEMP）脚本 %d 条"
          % (len(allx), len(allx) - len(external), len(external)))
    assert len(external) > 0, "[FAIL] 仓库外脚本数为 0 —— manifest 解析或口径失效（历史 46/98）"
    copied = skipped = 0
    for x in external:
        src = Path(x["cmd"][1])
        assert src.exists(), "源脚本不存在：%s（tag=%s）" % (src, x["tag"])
        rel = "tools/regression/archive/%s/%s" % (x["tag"], src.name)
        dst = ROOT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        h = sha(src)
        if dst.exists() and sha(dst) == h:
            skipped += 1
        else:
            shutil.copyfile(src, dst)
            copied += 1
        items[rel] = {"original": str(src).replace("\\", "/"), "tag": x["tag"], "sha256": h,
                      "bytes": src.stat().st_size}
    idx["items"] = items
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                     encoding="utf-8", newline="\n")
    print("归仓完成：新复制 %d / 已一致跳过 %d / 索引条目 %d" % (copied, skipped, len(items)))
    print("索引 = %s" % INDEX)
    assert len(items) == len(external), \
        "[FAIL] 索引条目 %d != 仓库外脚本 %d（判据失效）" % (len(items), len(external))
    return 0


def do_check():
    idx = load_index()
    items = idx["items"]
    if not items:
        print("[FAIL] 归仓索引为空 —— 判据不可用（历史 128/141）")
        return 1
    bad, lost, ok = [], [], 0
    for rel, meta in sorted(items.items()):
        a = ROOT / rel
        o = Path(meta["original"])
        if not a.exists():
            bad.append("%s（归档缺失）" % rel)
            continue
        if sha(a) != meta["sha256"]:
            bad.append("%s（归档内容与索引 sha256 不一致）" % rel)
            continue
        if not o.exists():
            lost.append(rel)
            continue
        if sha(o) != meta["sha256"]:
            bad.append("%s（原文件与归档不一致：%s）" % (rel, o))
            continue
        ok += 1
    print("归仓复核：索引 %d 条 → 归档与原文件逐字节一致 %d 条；原文件已丢失 %d 条；异常 %d 条"
          % (len(items), ok, len(lost), len(bad)))
    print("正向对照：索引条目 %d > 0 ⇒ %s" % (len(items), "PASS" if len(items) > 0 else "FAIL"))
    for b in bad:
        print("  [FAIL] %s" % b)
    for l in lost:
        print("  原文件已丢失（可用 --restore 还原）：%s" % l)
    return 1 if bad else 0


def do_restore():
    idx = load_index()
    items = idx["items"]
    back = 0
    for rel, meta in sorted(items.items()):
        a = ROOT / rel
        o = Path(meta["original"])
        if not a.exists():
            print("[FAIL] 归档缺失，无法还原：%s" % rel)
            return 1
        if o.exists() and sha(o) == meta["sha256"]:
            continue
        o.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(a, o)
        back += 1
        print("  还原：%s" % o)
    print("还原完成：%d 个文件（其余按 sha256 判断为已存在且一致）" % back)
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(do_check())
    if "--restore" in sys.argv:
        sys.exit(do_restore())
    sys.exit(do_archive())
