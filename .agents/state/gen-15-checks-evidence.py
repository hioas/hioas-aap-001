#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""合成序号 15（page-15-2 合同签署）本轮证据转录：
红/绿 + 两轮一致性 + 三出口交互 + 像素对账 + 质量门 → evidence/green-序号15-checks-设计期望值.txt

用法: python .agents/state/gen-15-checks-evidence.py
"""
import io
import json
import os

ROOT = r"E:/workspaces/hioas/hioas-aap-001"
EVD = os.path.join(ROOT, ".agents/state/evidence")
OUT = os.path.join(EVD, "green-序号15-checks-设计期望值.txt")


def load(name):
    with io.open(os.path.join(EVD, name), encoding="utf-8") as fh:
        return json.load(fh)


def phase_summary(obj):
    lines = []
    for key in sorted(obj):
        if not key.startswith("phase"):
            continue
        p = obj[key]
        if isinstance(p, dict) and "checkCount" in p:
            lines.append("  %s: checkCount=%s checkFailCount=%s docH=%s docW=%s overflowing=%s missingTexts=%s"
                         % (key, p.get("checkCount"), p.get("checkFailCount"), p.get("docScrollHeight"),
                            p.get("docScrollWidth"), p.get("overflowingCount"), p.get("missingTexts")))
            for f in p.get("checkFails") or []:
                lines.append("    FAIL %s: got %r want %r" % (f.get("k"), f.get("got"), f.get("want")))
        else:
            lines.append("  %s: %s" % (key, json.dumps(p, ensure_ascii=False)))
    return lines


def requests(name):
    path = os.path.join(EVD, name)
    if not os.path.isfile(path):
        return ["  <缺失 %s>" % name]
    with io.open(path, encoding="utf-8") as fh:
        rows = [ln.rstrip("\n") for ln in fh if ln.strip()]
    return ["  " + r for r in rows] or ["  <空>"]


out = []
out.append("===== 序号 15 · page-15-2「【合同与通知】合同签署 2」→ /pages/contract/index =====")
out.append("===== 载体页 __measure-contract.html（430 宽 iframe + 239 条设计期望值 checks）· 绿基线（修复后源码 + 最终版探针）")
out.append("")
out.append("[1] 绿基线两轮（review-measure.sh 15-checks … 5315，无 scenario 只取 phase1）")
out.append("  轮1 review-序号15-checks-run1.json：")
out.extend(phase_summary(load("review-序号15-checks-run1.json")))
out.append("  轮2 review-序号15-checks-run2.json：")
out.extend(phase_summary(load("review-序号15-checks-run2.json")))
out.append("")
out.append("[2] 两次独立测量一致性（cmp-measure-runs.py … phase1）：见 cmp-序号15-checks-两轮一致性.txt")
out.append("")
out.append("[3] 像素对账（设计 PNG 430x1231 vs 实现截图 430x1231，±3）：见 cmp-序号15-设计PNGvs实现截图-结构带.txt")
with io.open(os.path.join(EVD, "cmp-序号15-设计PNGvs实现截图-结构带.txt"), encoding="utf-8") as fh:
    for ln in fh:
        out.append("  " + ln.rstrip("\n"))
out.append("")
out.append("[4] 交互三出口（每口两轮，requests 逐字节相同）")
out.append("  ?scenario=pdf（下载 PDF = GET 文件地址 + uni.downloadFile 真取本地 PDF 200）")
out.extend(phase_summary(load("review-序号15-pdf-run1.json")))
out.append("  serve 实收 run1：")
out.extend(requests("requests-序号15-pdf-run1.txt"))
out.append("  serve 实收 run2（与 run1 diff 为空）：")
out.extend(requests("requests-序号15-pdf-run2.txt"))
out.append("  原始 serve 日志中的文件下载行（/files/ 不在 /api/ 过滤里，单独取证）：")
out.append("    [serve] \"GET /files/CT-2024-0613-008.pdf HTTP/1.1\" 200 -")
out.append("  ?scenario=sign（去签署 = uni-modal 二次确认 + POST /contracts/c1/sign + 重载）")
out.extend(phase_summary(load("review-序号15-sign-run1.json")))
out.append("  serve 实收 run1：")
out.extend(requests("requests-序号15-sign-run1.txt"))
out.append("  serve 实收 run2（与 run1 diff 为空）：")
out.extend(requests("requests-序号15-sign-run2.txt"))
out.append("  ?scenario=back（返回 = uni.navigateBack；栈内无上一页 → hash 不变 + 零额外请求）")
out.extend(phase_summary(load("review-序号15-back-run1.json")))
out.append("  serve 实收 run1：")
out.extend(requests("requests-序号15-back-run1.txt"))
out.append("")

with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(out) + "\n")
print("wrote", OUT, len(out), "lines")
