# -*- coding: utf-8 -*-
"""把序号 5（page-5-2「【检测验真】检测进行中 2」）判定的「非偏差」登记进 textleaf-accept.json。

判据优先级：①设计显式 height ②design PNG 的盒/带实测（含盒算术）③fs × lineHeight；②③冲突以 ② 为准。

本轮红基线（`textleaf-scan.py 5` → `textleaf-audit.py 5`）**待判读 class 8**，逐条判读后**全部为非偏差**
（无源码改动），证据分三类：

A. 判据①「同帧同字号的显式 height」（本帧设计自己给出的行盒，最硬）:
     fs15 `ea3a0a0d`（分项检测）        → height=22
     fs13 `1fe5e490` 等 8 条（D1..D8 标题）→ height=18
     fs12 `ff72fdea`（检测期间已启用成本保护）→ height=18
     fs11 `f44b1675` + 8 条 D 行副行 + …（共 9 条）→ height=16
   取证: python .agents/state/leaves-5.py page-5-2

B. 判据②「design PNG 盒/带实测」+ 盒算术（整页闭合）:
   卡1（88f1ee17，padding 20，fit_content）= 20 + 标题行 T + 16 + 进度条 10 + 12 + 元信息行 M + 16 + 成本块 58 + 20
   design PNG 与实现截图在**同一列同一窗口**逐带相同：
     x=25 卡1 白带        110..301(192)  = 110..301(192)   ← 卡1 上下界一致
     x=60 进度条蓝带      170..179(10)   = 170..179(10)    ← 卡顶 108 + 20 + T + 16 = 170 ⇒ **T = 26**
     x=60 成本块 #ECFDF5  226..283       = 226..283        ← 108 + 20+T+16+10+12+M+16 = 208+M = 226 ⇒ **M = 18**
   ⇒ 标题行 26 = max(标题 22, 58% 行盒) ⇒ `card__percent` 行盒 **26**；按声明模型 20×1.2 = 24 会让标题行
     24、进度条上移到 168（与两侧 PNG 的 170 冲突）。
   提示卡（c960eff4，padding [16,20,16,20]）：x=25 白带 765..830(66) 两侧**相同** ⇒ 卡高 72 = 16 + content 40 + 16；
     文案两行墨迹 **设计 785..795 / 800..810（行距 16）· 实现 785..795 / 801..811（行距 16）** ⇒ 该块的
     行盒就是 16（声明模型 12×1.2 = 14.4 会给出行距 14.4），且 40 = 该 2 行块在盒内居中（非顶对齐）。

C. 判据①/②给出的「不承重」类（定高盒内居中，两模型对墨迹同解）:
   顶部状态胶囊 h24（x=410 近右圆角带 58..73 两侧**相同**）· D 行状态胶囊 h22（x=380 带 380..401 两侧**相同**）·
   底栏按钮 h48（x=140 按钮带 862..909 两侧**相同**，底栏 84 = 12+48+24）—— 三处文本行盒不参与布局，
   且各文本的墨迹中心两侧**完全相同**（差 0.0 行）。

逐类墨迹与盒带明细见 evidence/cmp-序号5-文本叶子行盒-逐类带.txt（脚本 .agents/state/tl-5-evidence.py，
设计 PNG = .agents/state/design-shots/page-5-2.png 430×934，sha256 b64ef9e8…，与重抓帧的新导出图逐字节相同）。

用法: python .agents/state/accept-5-textleaf.py [--dry] [--reset]
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'textleaf-accept.json')
PAGE = 'page-5-2'
TAG = '5'
AT = '2026-09-16 21:2x'
EVID = ('evidence/cmp-序号5-文本叶子行盒-逐类带.txt + evidence/review-序号5-textleaf-报告.md'
        ' + design-shots/page-5-2.png（430×934 · sha256 b64ef9e8…，与重抓帧的新导出图逐字节相同）')
PNG = 'design PNG（430×934）'
FH16 = ('判据①同帧显式 height：本帧 fs11 有 9 个叶子显式 height=16（`f44b1675` 成本信息副行 + '
        '`cc4105a8`/`f91842a8`/`8140ada2`/`52d6726b`/`1378b642`/`2c1dafd9`/`ce8830a1`/`1f963553` 八条 D 行副行）'
        '⇒ 该帧 fs11 的渲染行盒就是 16（声明模型 11×1.2 = 13.2 只是审计口径）。')
CHIP = ('判据②不承重：胶囊是定高盒（顶部 24 / 行内 22）+ alignItems=center ⇒ 文本行盒不参与布局。')
ITEMS = [
    ('card__percent',
     'fs20 × lh1.2 = 24（fit_content，卡1 标题行右侧）', 'line-height 26',
     '判据②+③盒算术：卡1 = 20 + 标题行 T + 16 + 进度条 10 + 12 + 元信息行 M + 16 + 成本块 58 + 20 = 196。'
     + PNG + ' 与实现截图在 x=60 列的**进度条蓝带逐行相同（170..179）**、x=25 的**卡1 白带逐段相同（110..301）**、'
     'x=60 的成本块**起点同为 226** ⇒ T = 170 − 108 − 20 − 16 = **26**、M = 226 − 208 = **18**。'
     '标题行 = max(标题 22, 58% 行盒) ⇒ 58% 的行盒必为 26（若按声明 24，标题行 24、进度条会落在 168）。'
     '墨迹：设计 134..149(16) vs 实现 134..149(16)，中心 141.5 = 141.5（差 0.0）。'),
    ('card__title',
     'fs15 × lh1.2 = 18（fit_content，卡1「总进度」）', 'line-height 22',
     '判据①同帧显式 height：本帧 fs15 的 `ea3a0a0d`（分项检测）**显式 height=22** ⇒ 该帧 fs15 渲染行盒 = 22；'
     '且卡1 标题行 26 由 58% 的行盒（26）决定，标题 22 不承重（见 card__percent 条的 T 链）。'
     '墨迹：设计 134..148(15) vs 实现 134..148(15)，中心 141.0 = 141.0（差 0.0）。'),
    ('chip__text',
     'fs11 × lh1.2 = 13.2（fit_content，顶部状态胶囊 + 3 个行内胶囊）', 'line-height 16',
     FH16 + ' ' + CHIP + ' 硬证据：顶部胶囊盒在 x=410（近右圆角）**两侧同为 58..73**、D1 行胶囊盒在 x=380 '
     '**两侧同为 380..401**（h22）；顶部胶囊文案墨迹 设计 61..70(10) vs 实现 62..71(10)，中心 65.5 = 65.5（+0.0）、'
     '带高相同（±1 为 H5 回退字体）。'),
    ('history-bar__text',
     'fs14 × lh1.2 = 16.8（fit_content，底栏「查看历史检测报告」）', 'line-height 20',
     '判据②不承重：该文本在 `查看历史报告按钮 73a98024`（**h=48 定高** + alignItems=center）内 ⇒ 行盒不参与布局；'
     '底栏 84 = 12 + 48 + 24 与两侧 PNG 一致（x=140 按钮带 **862..909 逐行相同**）。'
     '墨迹：设计 878..895(18) vs 实现 880..893(14) —— 带高差来自设计字体（SourceHanSans）与 H5 回退字体的字形墨迹高度，'
     '**墨迹中心完全相同（886.5 = 886.5，差 0.0）** ⇒ 行盒差异对墨迹无影响。'),
    ('meta__done',
     'fs12 × lh1.2 = 14.4（fit_content，卡1 元信息行左侧）', 'line-height 18',
     '判据①+②：本帧 fs12 的 `ff72fdea`（检测期间已启用成本保护）**显式 height=18**；'
     '盒算术 卡1 的成本块起点 226（两侧 PNG 相同）= 108 + 20 + T26 + 16 + 10 + 12 + M + 16 ⇒ **M = 18**。'
     '墨迹：设计 196..206(11) vs 实现 196..206(11)，中心 201.0 = 201.0（差 0.0）。'),
    ('meta__eta',
     'fs12 × lh1.2 = 14.4（fit_content，卡1 元信息行右侧）', 'line-height 18',
     '同 meta__done：同一元信息行（`dac2c177` horizontal / align center / fit_content）内的右侧文本，'
     '行盒由该行两个 fs12 文本共同决定 = 18（判据① `ff72fdea` h=18 + 判据② 卡1 闭合 M = 18）。'
     '墨迹（同窗口）：设计 196..206(11) vs 实现 196..206(11)。'),
    ('probe-chip__text',
     'fs11 × lh1.2 = 13.2（fit_content，D1..D8 行内状态胶囊文案 16 处）', 'line-height 16',
     FH16 + ' ' + CHIP + ' 硬证据：D1 行胶囊盒（#ECFDF5，x=380）**两侧同为 380..401（22 行）**、'
     'D1 文案「完成」墨迹 设计 385..395(11) vs 实现 386..396(11)，中心 390.5 = 390.5（差 0.0）。'),
    ('tip__text',
     'fs12 × lh1.2 = 14.4（fit_content，提示卡文案 2 行）', 'line-height 16',
     '判据②design PNG 实测（②与③冲突，以 ② 为准）：提示卡 `c960eff4`（padding [16,20,16,20]）'
     '的 x=25 白带 **765..830(66) 两侧相同** ⇒ 卡高 72 = 16 + content 40 + 16；'
     '文案两行墨迹 **设计 785..795 / 800..810（行距 16）· 实现 785..795 / 801..811（行距 16）**'
     '⇒ 该文本块的**行盒就是 16**（按声明的 14.4 会得到行距 14.4，与设计 PNG 的 16 冲突），'
     '且 40 高的块由 2 行（2×16 = 32）在盒内居中（若按 14.4 顶对齐，两行墨迹会整体上移约 4 行）。'
     '墨迹中心 797.5 vs 798.0（差 0.5 = H5 回退字体）。'),
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
