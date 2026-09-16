# -*- coding: utf-8 -*-
"""往 gen-review-report.sh 的「差异判读」段追加本轮的两条（序号1 fixture 缺口 before/after、序号1/2 偏差清零 + 老留证对比）。

插在收尾的 `} > "$OUT" 2>&1` 之前；新增行不使用反引号，避免转义漂移。
"""
import io
import os

PATH = os.path.join(".agents", "state", "gen-review-report.sh")
ANCHOR = '} > "$OUT" 2>&1'

LINES = [
    '  echo',
    '  echo "6. **序号 1 — 测量面 fixture 缺口，本轮已补齐（red → green）**：登录页点「获取验证码」/「登录 / 注册」发的是 POST /api/v1/auth/sms/send 与 POST /api/v1/auth/sms/login，而 api/ 目录里没有这两个 fixture → serve.py 回通用 {\\"code\\":\\"0\\",\\"data\\":{\\"id\\":\\"c1\\"}}，页面拿到 res.token === undefined。"',
    '  echo "   - fixture 体检红基线：\\`python .agents/state/check-mock-fixtures.py --mock api-tmp-noauth\\`（同目录去掉 v1/auth）→ FAIL 2（缺键 ttl / token,role），证据 evidence/red-mock-fixture-auth.txt；补上两个 fixture 后 --mock api → 全部 PASS（evidence/green-mock-fixture-auth.txt）。"',
    '  echo "   - **同探针 before/after**（\\`__measure-login.html\\` phase6）：before（api-tmp-noauth，evidence/review-序号1-red-run{1,2}.json）→ localStorage aap_token = {\\"type\\":\\"undefined\\"}（等于没写进真 token）；after → aap_token = tk-mock-001 且 hash 跳到 /pages/workbench/index。"',
    '  echo "7. **序号 1 登录注册 — 逐项偏差 49 → 0**：载体页 93 条设计期望值，修前 49 条不符（品牌区结构、卡片/输入框/按钮尺寸与色值、字段间距、免责卡），修后 0 条；两轮独立测量全等。修前逐条清单见 evidence/red-序号12-修前偏差-转录.txt。"',
    '  echo "8. **序号 2 工作台 — 逐项偏差 7 → 0**：92 条设计期望值里 7 条色值不符（小标题 rgb(71,85,105)→rgb(100,116,139)、图例值/指标标签/条行值/合计行 rgb(100,116,139)→rgb(148,163,184)、待办文字 rgb(15,23,42)→rgb(51,65,85)、模型序号四行文字色需逐行给色），修后 0 条。"',
    '  echo "   - 与建页老留证（measure-序号2-修后.json，扁平结构）的跨代对比见 evidence/cmp-序号2-老留证vs本轮.txt：公共键 16 → 相同 12，4 处差异全部 = 老留证那轮 iframe 有可见滚动条（innerWidth 同为 430 但 docScrollWidth 415）：docScrollWidth/avatarRight/todoChevronRight 各 +15，条填宽度 95→102（42% × 轨道宽，轨道宽随内容宽 +15）。"',
    '  echo "9. **已知的刻意偏差（沿用台账口径，不算缺陷）**：工作台内容区底部 padding 用 96px 而设计是 0（+ 末尾 16px 占位）——因为底部 TabBar 按 position:fixed 实现（设计画布是随内容排在最后的独立 frame），留白用于避免最后一张卡被固定栏遮住；DOM 断言 tabbarPinned=true 固定住这一口径。"',
]

NEW = "\n".join(LINES) + "\n"


def main():
    with io.open(PATH, encoding="utf-8") as fh:
        text = fh.read()
    if "序号 1 — 测量面 fixture 缺口" in text:
        print("已追加过，跳过")
        return 0
    if ANCHOR not in text:
        raise SystemExit("未找到收尾锚点")
    text = text.replace(ANCHOR, NEW + ANCHOR, 1)
    with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("appended %d lines" % len(LINES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
