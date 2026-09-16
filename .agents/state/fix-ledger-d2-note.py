# -*- coding: utf-8 -*-
"""修掉台账序号 2 备注里被 bash 反引号命令替换吃掉的一段（`onQuick` 变成空）。

原因：上一条 append-ledger-note 的 --note 参数里带了反引号，bash 先做了命令替换。
本脚本直接在 CSV 里把错段替换成正确文本，然后交回给 normalize-ledger-eol.py 统一行尾。
"""
import io
import os

PATH = os.path.join(".agents", "state", "aap-feature-status.csv")
BAD = "快捷入口「钱包」整项删除（ 的 client-only toast 分支一并删掉）"
GOOD = "快捷入口「钱包」整项删除（onQuick 里 client-only toast 分支一并删掉）"


def main():
    with io.open(PATH, encoding="utf-8", newline="") as fh:
        text = fh.read()
    if BAD not in text:
        print("未找到错段（可能已修）")
        return 0
    text = text.replace(BAD, GOOD)
    with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("fixed: %s -> %s" % (BAD[:20], GOOD[:24]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
