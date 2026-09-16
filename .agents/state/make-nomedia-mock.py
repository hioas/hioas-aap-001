#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""重建 D3 的 nomedia mock 变体（可复现，替代手工改 JSON 的临时目录）。

用途：序号 2 工作台「图例缺字段 → 占位符、不显示 0%」的实测场景
（决策 D3 验收 (c)）：把基础 mock `api` 复制成 `api-tmp-d3-nomedia`，
并删掉 `v1/usage/summary` 里的 `audio_input_tokens` / `video_input_tokens` 两个字段
（模拟服务端未返回这两类 —— 18-API 无字段级 schema，缺字段必须占位）。

用法:
  python .agents/state/make-nomedia-mock.py            # 重建变体
  python .agents/state/make-nomedia-mock.py --clean    # 用完删除（仓库不留临时目录）
"""
import json
import os
import shutil
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "h5-measure")
SRC = os.path.join(BASE, "api")
DST = os.path.join(BASE, "api-tmp-d3-nomedia")
STRIP = ("audio_input_tokens", "video_input_tokens")
SUMMARY_REL = os.path.join("v1", "usage", "summary")


def main():
    args = sys.argv[1:]
    if args and args[0] == "--clean":
        if os.path.isdir(DST):
            shutil.rmtree(DST)
            print("removed %s" % DST)
        else:
            print("not found %s" % DST)
        return 0

    if os.path.isdir(DST):
        shutil.rmtree(DST)
    shutil.copytree(SRC, DST)

    path = os.path.join(DST, SUMMARY_REL)
    with open(path, "r", encoding="utf-8") as fh:
        body = json.load(fh)
    removed = []
    for key in STRIP:
        if key in body.get("data", {}):
            body["data"].pop(key)
            removed.append(key)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(body, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("created %s (removed=%s)" % (DST, ",".join(removed)))
    print("summary keys: %s" % ",".join(sorted(body["data"].keys())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
