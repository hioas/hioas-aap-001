# -*- coding: utf-8 -*-
"""把 gen-review-report.sh 里遗留的「**[本轮复跑]**」标记改成「（上一轮 08:30 留证）」——
本轮只复跑了序号 1 / 2 及其变体，3~23 行的 review 文件是上一轮产物，标「本轮复跑」会误导。
"""
import io
import os

PATH = os.path.join(".agents", "state", "gen-review-report.sh")

OLD_LEGEND = (
    '  echo "- 标记: **[本轮复跑]** = 本轮的 review-序号*-run{1,2}.json 已重写；'
    '其余行为上一轮留证（文件未变，仍可复现判读）。"'
)
NEW_LEGEND = (
    '  echo "- 标记: **[本轮新增]** = 本轮的 review-序号*-run{1,2}.json 新写；'
    '（上一轮 08:30 留证）= 文件未变、仍可复现判读，本轮未重跑。"'
)


def main():
    with io.open(PATH, encoding="utf-8") as fh:
        text = fh.read()
    n1 = text.count(OLD_LEGEND)
    text = text.replace(OLD_LEGEND, NEW_LEGEND)
    n2 = text.count("**[本轮复跑]**")
    text = text.replace("**[本轮复跑]**", "（上一轮 08:30 留证）")
    with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("legend replaced=%d, markers replaced=%d" % (n1, n2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
