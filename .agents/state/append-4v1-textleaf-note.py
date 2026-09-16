# -*- coding: utf-8 -*-
"""给台账序号 4-v1 行追加「用例(证据)」与「备注」（csv.DictWriter 重写整表，字段数校验另跑）。

用法: python .agents/state/append-4v1-textleaf-note.py [--dry]
规则（§5.16）：追加文本里不放 ASCII 双引号；备注列历史为不带引号字段 → 也不放 ASCII 逗号（用 · 与 （））。
"""
import csv
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'aap-feature-status.csv')
SEQ = '4-v1'

CASE = (
    '文本叶子维度收口 2026-09-16 21:1x（cron 轮 aap-tdd-run-20260916-2046）：textleaf-scan.py 4-v1'
    '（mock api · 路由 /pages/credential-submit/form · leafs 26 · docH 1071 空态）+ textleaf-audit.py '
    '红基线 **待判读 class 8** → 逐条判读（判据 ①同帧显式 height ②design PNG 盒/盒算术 ③fs×lh）→ '
    '8 条**全部非偏差**并登记 textleaf-accept.json（page-24 +8 键）→ 复跑 **待判读 0 · 已核定 8**；'
    '新增 star.lineHeight check（phase2 **249→250** 条）并以**源码变异**证明有牙齿'
    '（.field__star line-height 18→14.4 → FAIL star.lineHeight got 14.4 want 18 → git checkout 还原 → 250 条 0 失败 ×2）；'
    '回归门 review-measure.sh 4v1-tl 两轮：phase1 全等 32/32 · phase2 全等 33/33 · 不一致 0 · docH **1137 = 设计帧高** · '
    '溢出 0 · 文案缺失 0 · serve 实收 12 行排序后集合逐字节相同（1 条真实 POST /api/v1/provider/qualifications + 落地页 detecting 5 对轮询 GET）；'
    '证据 evidence/{red-序号4v1-textleaf-待判读.txt · green-序号4v1-textleaf-待判读0.txt · cmp-序号4v1-文本叶子-逐类带.txt · '
    'red-序号4v1-starcheck-变异测试.txt · review-序号4v1-textleaf-报告.md} + .agents/state/evidence/review-序号4v1-{tl,tlmut}-run{1,2}.json + '
    '截图 logs/screenshots/20260916-2115-序号4v1-接入凭证表单-textleaf轮-h5-430宽.png（440×1240 载体页 × 430 宽 iframe）'
)

NOTE = (
    '文本叶子维度（序号 4-v1）收口 2026-09-16 21:1x：8 条待判读 class —— card__title · card__tip · field__label · '
    'field__star · type-chip__text · footnote__text · uni-input-placeholder · uni-textarea-placeholder —— '
    '全部判「非偏差」：判据 ①**同帧显式 height**（fs11 的 d09f9feb“单个文件不超过 10MB”/919871df“2.4 MB”显式 h16 · '
    'fs13 的 ee12aef8“点击上传凭证文件”显式 h20 · fs12 的 7549512f 显式 h18）②**盒算术**（设计 PNG 四张卡 388/98/274/118 与整页 '
    '1137 逐项闭合：标题行 20 · 标签行 18 · chip 行盒 18 · 备注框 12+20+24 · 提交提示 21+4；按声明的 fs×1.2 会让整页 ≈1124）'
    '③**逐类墨迹**与设计 PNG ±1 行（tl-bands 逐类带）。设计帧重抓（layer_id cb1de468-0658-4ccb-a1c3-46c2f48f6314）'
    'design.json sha256 bd249858… **逐字节相同** · 重抓新导出的设计 PNG sha256 f77955ca…（430×1137）与本轮下载**逐字节相同** ⇒ **无漂移**。'
    '另有 3 条「未渲染叶子」= 设计帧的示例数据（深圳市恒信科技有限公司 / 营业执照扫描件.pdf / 2.4 MB）—— textleaf 载体页只加载空态 '
    '故不渲染 · 其渲染路径由同载体页 phase2（真实 onPickFile 后的已上传态）覆盖并已断言 fileName/fileSize 文案与行盒。'
    '⚠️ **口径更正**：本页载体页 iframe 与台账「目标路由」均为 `/pages/credential-submit/form`（页面源码不读任何参数）—— '
    '§4 与上轮简报里写的「带参路由 /pages/credential-submit/form?id=c1」**作废**。'
    '本轮**无源码改动**（变异测试后已 git checkout 还原 · src 工作区干净）。'
)


def main():
    raw = io.open(P, 'r', encoding='utf-8', newline='').read()
    rows = list(csv.DictReader(io.StringIO(raw)))
    fields = list(rows[0].keys())
    hit = 0
    for r in rows:
        if r['序号'] == SEQ:
            r['用例(证据)'] = (r['用例(证据)'] or '') + ' ｜ ' + CASE
            r['备注'] = (r['备注'] or '') + ' ｜ ' + NOTE
            hit += 1
    print('命中 %d 行 · 序号 %s · 字段数 %d' % (hit, SEQ, len(fields)))
    if '--dry' in sys.argv:
        return
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=fields, lineterminator='\r\n')
    w.writeheader()
    w.writerows(rows)
    txt = out.getvalue()
    chk = list(csv.DictReader(io.StringIO(txt)))
    bad = [i for i, r in enumerate(chk, 2) if len(r) != len(fields) or None in r.values()]
    print('复解析：%d 行 · 字段异常行 %s' % (len(chk), bad or '无'))
    if bad:
        raise SystemExit('字段数体检未过 → 不落盘')
    io.open(P, 'w', encoding='utf-8', newline='').write(txt)
    print('已写盘 %s' % P)


main()
