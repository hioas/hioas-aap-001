"""序号 5（page-5-2 检测进行中 2）· 队列 8 checks 轮的证据转录。

用法: python .agents/state/gen-5-checks-evidence.py
产出:
  .agents/state/evidence/red-序号5-checks-设计期望值偏差.txt      红基线（修复前，两轮）
  .agents/state/evidence/green-序号5-checks-设计期望值.txt        绿（修复后，两轮 + 交互相）
  .agents/state/evidence/review-序号5-checks-报告.md             本轮报告
"""
import json
from pathlib import Path

EV = Path(".agents/state/evidence")


def load(name):
    return json.loads((EV / name).read_text(encoding="utf-8"))


def phase_lines(doc):
    out = []
    for key in sorted(doc.keys()):
        ph = doc[key]
        out.append(
            "{key}: checkCount={cc} checkFailCount={cf} overflowing={ov} docH={dh} docW={dw}".format(
                key=key,
                cc=ph.get("checkCount"),
                cf=ph.get("checkFailCount"),
                ov=ph.get("overflowingCount"),
                dh=ph.get("docScrollHeight"),
                dw=ph.get("docScrollWidth"),
            )
        )
        if "state" in ph:
            out.append("    state={} missingTexts={} percent={} finished={} eta={}".format(
                ph.get("state"), ph.get("missingTexts"), ph.get("percentText"),
                ph.get("finishedText"), ph.get("etaText")))
        if "scenario" in ph:
            out.append("    interaction=" + json.dumps(ph, ensure_ascii=False))
        for f in ph.get("checkFails") or []:
            out.append('    FAIL {k}: got "{got}" want "{want}"'.format(**f))
        if not ph.get("checkFails"):
            out.append("    （无失败项）")
    return out


def two_run(tag, title):
    lines = [title, ""]
    for run in (1, 2):
        doc = load("review-序号{tag}-run{run}.json".format(tag=tag, run=run))
        lines.append("=== run{run} ===".format(run=run))
        lines += phase_lines(doc)
        lines.append("")
    return lines


red = two_run("5-checks-red", "序号 5 · 修复前红基线（载体页 __measure-detecting.html 235 条设计期望值 checks）")
green = two_run("5-checks", "序号 5 · 修复后绿（同探针 235 条 checks）")
green += two_run("5-int", "序号 5 · 交互相（?scenario=interaction：查看历史检测报告 = client-only）")

# 实测请求（写入证据：证明「校验门/client-only 没偷偷发写请求」且轮询真实发生）
for tag in ("5-checks", "5-int"):
    for run in (1, 2):
        p = EV / "requests-序号{tag}-run{run}.txt".format(tag=tag, run=run)
        req = p.read_text(encoding="utf-8").strip().splitlines()
        green.append("=== requests 序号{tag}-run{run}（serve.py 实收，{n} 行） ===".format(tag=tag, run=run, n=len(req)))
        green += ["    " + r for r in req]
        green.append("")

(EV / "red-序号5-checks-设计期望值偏差.txt").write_text("\n".join(red) + "\n", encoding="utf-8")
(EV / "green-序号5-checks-设计期望值.txt").write_text("\n".join(green) + "\n", encoding="utf-8")

print("red 行数", len(red), "| green 行数", len(green))
for d in ("red-序号5-checks-设计期望值偏差.txt", "green-序号5-checks-设计期望值.txt"):
    print(d, (EV / d).stat().st_size, "bytes")
