# -*- coding: utf-8 -*-
"""在状态文件 §0 与 §5 补一条工具事实：cron 会话里 `hermes send -t feishu:oc_...` 会被跳过
（本 job 的最终回复自动投递到同一目标）→ 简报直接写进最终回复，别再浪费一次调用。

依据：2026-09-16 08:35 轮实测输出
"Skipped send_message to feishu:oc_7bb40d75cd345875ba9345a4fc599be2. This cron job will already
 auto-deliver its final response to that same target."
"""
import io
import os

PATH = os.path.join(".agents", "state", "aap-tdd-state.md")
NL = "\n"
ANCHOR = "## 1. 目标"
NOTE = (
    "> ⚠️ **cron 会话里不要再调 `hermes send -t feishu:oc_7bb40d75cd345875ba9345a4fc599be2`**：实测会被跳过"
    "（本 job 的最终回复自动投递到同一目标）。**简报与「⛔ 需要你拍板」都直接写进最终回复**即可，"
    "否则白丢一次工具调用（2026-09-16 08:35 轮实测）。" + NL + NL
)


def main():
    with io.open(PATH, encoding="utf-8", newline="") as fh:
        text = fh.read()
    if "cron 会话里不要再调" in text:
        print("已存在，跳过")
        return 0
    if ANCHOR not in text:
        raise SystemExit("未找到锚点 ## 1. 目标")
    text = text.replace(ANCHOR, NOTE + ANCHOR, 1)
    with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("state note added")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
