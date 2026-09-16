# -*- coding: utf-8 -*-
"""更新 gen-review-report.sh 的「覆盖面」说明与页面表（加入本轮新增的 1 / 1-red / 1-guard / 2 / 2-actions 行）。

用脚本改而不是 patch：文件里有大量 `\\`` 反引号转义，patch 工具容易发生转义漂移。
"""
import io
import os

PATH = os.path.join(".agents", "state", "gen-review-report.sh")

OLD_COVER = (
    '  echo "- 覆盖: 台账 22 行里 20 行有 \\`__measure-*.html\\` 载体页；'
    '序号 1（登录注册）/ 2（工作台）无载体页 → 待补（队列第 6 项）。"'
)
NEW_COVER = "\n".join(
    [
        '  echo "- 覆盖: 台账 22 行 **全部有 \\`__measure-*.html\\` 载体页**（本轮补上最后两行：序号 1 登录注册 / 序号 2 工作台）。"',
        '  echo "- 本轮新增维度: 载体页内置 **设计期望值 checks**（逐条 got/want）：登录页 93 项 / 工作台 92 项；\\`checkFailCount\\` 即「与设计稿的偏差条数」。"',
        '  echo "- 本轮新增证据: \\`requests-序号*-run{1,2}.txt\\`（该轮 serve 实收的 /api 请求行，写请求带 body）——「有没有发请求」不再靠页面自报。"',
    ]
)

TABLE_ANCHOR = "done <<'TABLE'\n"
NEW_ROWS = "\n".join(
    [
        "1|__measure-login.html|api|—|登录注册（本轮新增载体页）|**[本轮新增]**·checkFails 0/93",
        "1-red|__measure-login.html|api-tmp-noauth|—|登录注册·fixture 缺口 before（红）|**[本轮新增]**·与 after 对比见差异判读 1",
        "1-guard|__measure-login.html|api|—|登录注册·校验门（?scenario=guard，须零 POST）|**[本轮新增]**·requests 0 行",
        "2|__measure-workbench.html|api|—|工作台（本轮新增载体页）|**[本轮新增]**·checkFails 0/92",
        "2-actions|__measure-workbench.html|api|—|工作台·交互回放（钱包 client-only + Tab 我的）|**[本轮新增]**",
    ]
) + "\n"


def main():
    with io.open(PATH, encoding="utf-8") as fh:
        text = fh.read()
    if "__measure-login.html" in text:
        print("已更新过，跳过")
        return 0
    if OLD_COVER not in text:
        raise SystemExit("未找到覆盖说明行，需人工确认：\n%s" % OLD_COVER)
    text = text.replace(OLD_COVER, NEW_COVER)
    text = text.replace(TABLE_ANCHOR, TABLE_ANCHOR + NEW_ROWS, 1)
    with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("updated %s" % PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
