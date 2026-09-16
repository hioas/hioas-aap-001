# -*- coding: utf-8 -*-
"""把序号 4-v1（page-24「接入凭证-表单」）判定的「非偏差」登记进 textleaf-accept.json。

判据优先级：①设计显式 height ②design PNG 的盒/带实测（含盒算术）③fs × lineHeight；②③冲突以 ② 为准。

本轮红基线（`textleaf-scan.py 4-v1` → `textleaf-audit.py 4-v1`）**待判读 class 8**，全部判为**非偏差**（无需改源码），
理由分三类：
  A. 盒算术（判据②）：page-24 的四个卡都是 fit_content，但四张卡高在**设计与实现同为 388/98/274/118**
     （design PNG 430×1137 的 x=25 列色带 + DOM），其和必须闭合到整页 1137：
       顶部栏 74 = 16 + max(返回 36, 标题块 42) + 16
       基本信息卡 388 = 16 + 标题行 + 14 + 4×(标签行 + 8 + 输入框 44) + 3×14 + 16  ⇒ 标题行 20 · 标签行 18
       检测类型卡 98  = 16 + 标题行 + 12 + chip + 16 · chip = 8 + 行盒 + 8 = 34 ⇒ 行盒 18
       资料上传卡 274 = 16 + 标题行 + 12 + 上传区 144 + 12 + 文件行 54 + 16
       备注卡 118     = 16 + 标题行 + 10 + 备注框 56 + 16 · 备注框 = 12 + 行盒 + 24 ⇒ 行盒 20
       提交提示 25    = remixicon 字形盒 21(fs14×1.5) + padding-bottom 4
       整页 1137 = 74 + 16 + 388 + 16 + 98 + 16 + 274 + 16 + 118 + 16 + 48 + 16 + 25 + 16
     若按声明的 fs×lh1.2 落地（标题 16.8 / 标签 14.4 / chip 行 14.4 / 备注行 15.6），
     四张卡各短 3.2~5.6px、整页 1137 → 约 1124，与 design PNG 逐带冲突。
  B. 同帧显式 height（判据①的等价物）：该帧 fs11 的 `d09f9feb`（单个文件不超过 10MB）与 `919871df`（2.4 MB）
     都**显式 height=16**；fs13 的 `ee12aef8`（点击上传凭证文件）**显式 height=20**；fs12 的 `7549512f`
     显式 height=18 —— 即同帧同字号的设计行盒就是实现取值，声明模型的 fs×1.2 只是审计口径。
  C. 不承重：输入框（定高 44 + alignItems=center）与提交提示行（行高由 remicroicon 字形盒 21 定）里的文本
     行盒不参与布局，两个模型对墨迹同解。

逐类墨迹（`tl-bands.py`，窗口 = DOM 叶子 rect ±1 x / ±14 y，同一 x 窗口内设计与实现的 ink 带起点差 ≤1 行，
带高相同 ⇒ 渲染行盒一致）见 evidence/cmp-序号4v1-文本叶子-逐类带.txt。

另有 **3 条「未渲染叶子」= 设计帧的示例数据**（客户名称「深圳市恒信科技有限公司」/「营业执照扫描件.pdf」/「2.4 MB」）：
textleaf 载体页只加载**空态**，故不渲染；其渲染路径由同一载体页的 phase2（真实走 onPickFile 的已上传态）覆盖，
并已断言 fileName/fileSize 的文案与行盒（`__measure-form.html` 426/432 行）。

用法: python .agents/state/accept-4v1-textleaf.py [--dry] [--reset]
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'textleaf-accept.json')
PAGE = 'page-24'
TAG = '4-v1'
AT = '2026-09-16 21:10'
EVID = ('evidence/cmp-序号4v1-文本叶子-逐类带.txt + evidence/review-序号4v1-textleaf-报告.md'
        ' + .agents/state/evidence/review-序号4v1-tl-run{1,2}.json + design-shots/page-24.png（430×1137 · '
        'sha256 f77955ca…，与重抓帧的新导出图逐字节相同）')
PNG = 'design PNG（430×1137）'
CARD_ARITH = ("判据②盒算术：设计与实现在同一列 x=25 的白卡段**逐段相同**（94..473 / 498..587 / 612..877 / 902..1011）"
              "⇒ 卡片边界一致；卡 pitch 404/114/290 = 卡高 388/98/274 + 卡片间距 16（内容区 gap=16 为设计声明），"
              "且闭合到整页 1137 = 74 + 16 + 388 + 16 + 98 + 16 + 274 + 16 + 118 + 16 + 48 + 16 + 25 + 16；"
              "按声明模型会让四卡各短 3.2~5.6px。")
ITEMS = [
    ('card__title',
     'fs14 × lh1.2 = 16.8（fit_content，全部四张卡的标题行）', 'line-height 20',
     CARD_ARITH + ' 四张卡的「卡高 = 16 + 标题行 + gap + … + 16」都要标题行 = 20 才成立'
     '（基本信息 388 = 16+20+14+280+42+16 · 检测类型 98 = 16+20+12+34+16 · '
     '资料上传 274 = 16+20+12+144+12+54+16 · 备注 118 = 16+20+10+56+16）。'
     '逐类墨迹（4 处窗口）：基本信息 设计 109..122(51) vs 实现 110..123(51) · 检测类型 513..526(50) vs 514..527(50) · '
     '凭证资料 627..640(50) vs 628..641(51) · 备注 834..848 vs 834..847（±1 = H5 回退字体墨迹）。'),
    ('card__tip',
     'fs11 × lh1.2 = 13.2（fit_content）', 'line-height 16',
     '判据①同帧显式 height：本帧 fs11 的两个叶子 `d09f9feb`（单个文件不超过 10MB）与 `919871df`（2.4 MB）'
     '在设计里都**显式 height=16**（同名同字号 → 该帧 fs11 渲染行盒 = 16）。'
     '墨迹：设计 628..640(maxink 66) vs 实现 629..641(66) —— 带长相同、起点 +1（H5 回退字体）。'),
    ('field__label',
     'fs12 × lh1.2 = 14.4（fit_content）', 'line-height 18',
     '判据②盒算术：字段步进 70 = 标签行 18 + gap 8 + 输入框 44，四字段 280 与卡高 388 自洽；'
     '按 14.4 会让卡 1 短 14.4px。逐类墨迹（2 处）：客户名称 设计 143..154(43) vs 实现 143..154(42)'
     '（**起点逐值相同**）· 统一社会信用代码 227..239(85) vs 227..239(88)。'),
    ('field__star',
     'fs12 × lh1.2 = 14.4（fit_content）', 'line-height 18',
     '同一标签行（`field__label-row`，gap 4）内的必填星号：行盒由该行两个 fs12 文本的渲染行盒定，'
     '字段步进 70 与卡高 388 同样要求 18。墨迹（2 处）：设计 144..148(5) = 实现 144..148(6) · '
     '228..232(5) = 实现 228..232(6)（**起点逐值相同**）。'
     '⚠️ 本条此前在载体页无断言 → 本轮新增 `star.lineHeight` check（250 条）并以**源码变异**证明有牙齿'
     '（把 .field__star 的 line-height 临时改成 14.4px → `star.lineHeight: got 14.4 want 18` 1 条红 → '
     'git checkout 还原 → 250 条全绿两轮）。'),
    ('type-chip__text',
     'fs12 × lh1.2 = 14.4（fit_content）', 'line-height 18',
     '判据②盒算术：chip = padding 8 + 行盒 + 8 = 34，检测类型卡 98 = 16 + 标题行 20 + 12 + 34 + 16 自洽；'
     '按 14.4 会让 chip 30.8、卡 94.8（与 ' + PNG + ' 的卡片边界冲突）。'
     '逐类墨迹（3 处）：基础检测 553..564(46) vs 553..564(47) · 深度检测 553..564(46) 两侧相同 · '
     '合规检测 553..564(45) vs 553..564(46)（**起点逐值相同**）。'),
    ('footnote__text',
     'fs11 × lh1.2 = 13.2（fit_content）', 'line-height 16',
     '判据①+②不承重：提交提示行 `3f8c7ae8`（horizontal / align center / fit_content）的行高由同排 remixicon '
     '字形盒定 —— `a048d0c6` fs14 → 字形行盒 14×1.5 = 21；盒算术 提交提示 = 21 + padding-bottom 4 = 25，'
     '而整页 1137 的闭合正需要 25（见 card__title 条）。文本行盒 16 与 13.2 都不承重（居中盒内墨迹同解）。'
     '墨迹：设计 1101..1111(len 11) vs 实现 1102..1112(len 11)（起点 +1、带长相同）。'),
    ('uni-input-placeholder',
     'fs13 × lh1.2 = 15.6（fit_content，3 个输入框占位）', 'line-height 20',
     '判据①同帧显式 height：本帧 fs13 的 `ee12aef8`（点击上传凭证文件）**显式 height=20**；'
     '且输入框是定高 44 + alignItems=center ⇒ 占位行盒不参与布局，两模型对墨迹同解（差 <1px）。'
     '逐类墨迹（4 处）：请输入客户名称 设计 182..193(111) vs 实现 183..194(108)（+1）· '
     '请输入 18 位统一社会信用代码 266..277(130) vs 266..277(129)（**起点逐值相同**）· '
     '请输入联系人姓名 350..362(81) vs 350..361(79) · 请输入手机号 434..445(64) = 434..445(64)（**逐值相同**）。'),
    ('uni-textarea-placeholder',
     'fs13 × lh1.2 = 15.6（fit_content）', 'line-height 20',
     '判据②盒算术：备注框 `0e5a46b9` padding [12, 12, 24, 12] + 备注卡 118 = 16 + 标题行 20 + 10 + 备注框 56 + 16 '
     '⇒ 备注框 56 = 12 + 行盒 + 24 ⇒ **行盒 = 20**（声明模型 15.6 会给出 51.6，与 PNG 的卡 4 边界冲突）。'
     '墨迹：设计 917..923 vs 实现 918..923（起点 +1，窗口内带高相同）。'),
]


def main():
    data = json.load(io.open(P, encoding='utf-8'))
    if '--reset' in sys.argv:
        before = len(data['items'])
        data['items'] = [it for it in data['items'] if it.get('page') != PAGE]
        print('清空 %s 旧条目 %d 条' % (PAGE, before - len(data['items'])))
    have = {(it.get('page'), (it.get('class') or '').lstrip('.')) for it in data['items']}
    added = 0
    for cls, declared, impl, reason in ITEMS:
        if (PAGE, cls) in have:
            print('已存在：%s（跳过）' % cls)
            continue
        data['items'].append({
            'page': PAGE, 'tag': TAG, 'class': cls, 'declared': declared, 'impl': impl,
            'verdict': 'not-a-deviation', 'reason': reason, 'evidence': EVID, 'at': AT,
        })
        added += 1
    print('新增 %d 条（合计 %d 条）' % (added, len(data['items'])))
    if '--dry' not in sys.argv:
        io.open(P, 'w', encoding='utf-8', newline='').write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        print('已写盘 %s' % P)


main()
