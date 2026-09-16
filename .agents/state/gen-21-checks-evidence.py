#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""合成序号 21（page-21-2「【工作台与我的】我的 2」）checks 轮的证据转录：

  evidence/red-序号21-checks-设计期望值偏差.txt    红基线（最终版探针 + 未修改源码，两轮）+ 分诊
  evidence/green-序号21-checks-设计期望值.txt      绿基线（两轮 + 全等字段）+ 六个交互相出口 + serve 实收请求行

数据来源：.agents/state/evidence/review-序号21-*.json 与 requests-序号21-*.txt
用法：python .agents/state/gen-21-checks-evidence.py
"""
import io
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVD = os.path.join(ROOT, ".agents", "state", "evidence")


def load(tag):
    p = os.path.join(EVD, "review-序号%s.json" % tag)
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


def requests(tag):
    p = os.path.join(EVD, "requests-序号%s.txt" % tag)
    if not os.path.exists(p):
        return []
    with io.open(p, encoding="utf-8") as fh:
        return [l.rstrip("\n") for l in fh if l.strip()]


def phase_name(d):
    for k in d:
        if k.startswith("phase"):
            return k
    return None


def overview(d, tag, run):
    lines = []
    for name in sorted([k for k in d if k.startswith("phase")],
                       key=lambda s: (0 if s == "phase1" else 1, s)):
        p = d[name]
        if not isinstance(p, dict):
            continue
        lines.append("  %-7s checkCount=%s checkFailCount=%s docH=%s docW=%s overflowing=%s"
                     % (name, p.get("checkCount"), p.get("checkFailCount"),
                        p.get("docScrollHeight"), p.get("docScrollWidth"), p.get("overflowingCount")))
        for f in (p.get("checkFails") or []):
            lines.append("      FAIL %s: got %r want %r" % (f.get("k"), f.get("got"), f.get("want")))
        if p.get("missingTexts"):
            lines.append("      missingTexts=%r" % (p["missingTexts"],))
        if p.get("scenario"):
            lines.append("      scenario=%s payload=%s" % (p["scenario"], json.dumps(
                {k: v for k, v in p.items() if k not in ("checkCount", "checkFailCount", "checkFails")},
                ensure_ascii=False)))
    return lines


def main():
    out_red = []
    out_red.append("序号 21 / page-21-2「【工作台与我的】我的 2」→ /pages/mine/index")
    out_red.append("红基线：**最终版探针**（__measure-mine.html，230 条 checks，由 build-probe-21.py 从 __measure-messages.html 切骨架生成）")
    out_red.append("        + **未修改的页面源码**（修复前），430 宽 iframe 无头 Chrome 实测两轮。")
    out_red.append("命令：bash .agents/state/review-measure.sh 21-checks-red __measure-mine.html .agents/state/h5-measure/api-21 5341")
    out_red.append("")
    for i in (1, 2):
        out_red.append("--- run%d ---" % i)
        out_red.extend(overview(load("21-checks-red-run%d" % i), "21-checks-red", i))
        out_red.append("  serve 实收请求行 %d 行：%s" % (len(requests("21-checks-red-run%d" % i)),
                                                    " / ".join(requests("21-checks-red-run%d" % i))))
    out_red.append("")
    out_red.append("红基线分诊（哪条算页面缺陷、哪条是探针自身口径 bug）：")
    out_red.append("  · 探针自身 2 类期望值 bug（本轮先踩到、写进探针后重跑红基线，红/绿同版探针）：")
    out_red.append("      ① head.tags.top 我按「标签行」写 want 82，而实现里 .head__tags 本身就是带 padding-top 8 的容器")
    out_red.append("         （设计是「容器 a3c59082 + 子行 标签行」两层）→ 改为断容器盒 74 + 新增 .head__type.top = 82")
    out_red.append("      ② entries.values 我按 3 个值写 want，漏了第 5 行「我的消息」的「待阅读 3」（设计 row5 确实有值节点）")
    out_red.append("         → 改为 4 个值 + 4 个右边 + 4 个色（第 4 个是设计字面量 #000000，逐值断言不统一）")
    out_red.append("  · 其余 17 条全部是页面缺陷（本轮修掉的 10 类）：")
    out_red.append("      头像字形盒 16×16（设计 85003c7e fs30 声明 w33 → 33×45）·")
    out_red.append("      4 处文本行盒未按设计 lineHeight 1.2（类型标签/已认证 16→13.2 · 钱包标题 21→16.8 · 提现文案 20→15.6）·")
    out_red.append("      行图标字形盒 16×16（设计声明 w20、行盒 fs18×1.5=27 → 20×27，x 44→42、top 逐行 +6）·")
    out_red.append("      行标签行盒 19.5→15.6 · 行值行盒 18→14.4 · 胶囊文字行盒 14→12 ·")
    out_red.append("      字形颜色读不到（形状原在元素自身 background，改为 ::before + currentColor 后由伪元素承载）")
    with io.open(os.path.join(EVD, "red-序号21-checks-设计期望值偏差.txt"), "w",
                 encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out_red) + "\n")

    out_green = []
    out_green.append("序号 21 / page-21-2「【工作台与我的】我的 2」→ /pages/mine/index")
    out_green.append("绿基线：修复后 + 同一份最终版探针，430 宽 iframe 无头 Chrome 实测两轮。")
    out_green.append("命令：bash .agents/state/review-measure.sh 21-checks __measure-mine.html .agents/state/h5-measure/api-21 5342")
    out_green.append("")
    for i in (1, 2):
        out_green.append("--- run%d ---" % i)
        out_green.extend(overview(load("21-checks-run%d" % i), "21-checks", i))
        out_green.append("  serve 实收请求行 %d 行：%s" % (len(requests("21-checks-run%d" % i)),
                                                   " / ".join(requests("21-checks-run%d" % i))))
    out_green.append("")
    cmpout = subprocess.run([sys.executable, os.path.join(ROOT, ".agents", "state", "cmp-measure-runs.py"),
                             os.path.join(EVD, "review-序号21-checks-run1.json"),
                             os.path.join(EVD, "review-序号21-checks-run2.json"), "phase1"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out_green.append("两次独立测量一致性（cmp-measure-runs.py phase1）：")
    out_green.append(cmpout.stdout.decode("utf-8", "replace").strip())
    out_green.append("")
    out_green.append("交互相出口（每个场景各两轮；requests 用「集合相等」比对 —— 首屏 7 个 GET 是 Promise.all 并发，")
    out_green.append("落盘顺序会抖动，集合相同即证明请求集合一致，逐字节比对只在确定性场景（rows-quotes）成立）：")
    for tag, desc in [
        ("21-withdraw", "点「提现」= client-only 占位（missing-prd：18-API 无提现端点）"),
        ("21-rows-quotes", "点「我的报价单」→ /pages/quotes/index"),
        ("21-usage", "点「用量与对账」→ /pages/usage/index（序号 22 已实现，旧台账「未实现 → 降级」口径作废）"),
        ("21-settings", "点「账号与设置」→ /pages/settings/index（序号 23 已实现）"),
        ("21-tab-workbench", "TabBar「工作台」→ /pages/workbench/index"),
        ("21-tab-mine", "TabBar「我的」= 当前模块 → hash 不变"),
    ]:
        out_green.append("")
        out_green.append("--- %s：%s ---" % (tag, desc))
        for i in (1, 2):
            d = load("%s-run%d" % (tag, i))
            out_green.extend(overview(d, "%s-run%d" % (tag, i), i))
        r1 = requests("%s-run1" % tag)
        r2 = requests("%s-run2" % tag)
        out_green.append("  requests 集合相等=%s（run1 %d 行 / run2 %d 行）" % (sorted(r1) == sorted(r2), len(r1), len(r2)))
        out_green.append("  run1 请求行：" + " / ".join(r1))
    out_green.append("")
    out_green.append("共用组件回归门（AppTabBar 被 page-20-2 与 page-21-2 共用）：")
    out_green.append("  命令：bash .agents/state/review-measure.sh 21-sibling20 __measure-messages.html .agents/state/h5-measure/api-20 5350")
    for i in (1, 2):
        out_green.append("  --- run%d ---" % i)
        out_green.extend(overview(load("21-sibling20-run%d" % i), "21-sibling20", i))
    with io.open(os.path.join(EVD, "green-序号21-checks-设计期望值.txt"), "w",
                 encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out_green) + "\n")
    print("wrote red/green evidence for 序号 21")
    print("red lines:", len(out_red), "green lines:", len(out_green))


if __name__ == "__main__":
    main()
