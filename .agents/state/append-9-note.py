# -*- coding: utf-8 -*-
"""序号 9 checks 轮的台账追加（长文本走文件，避免命令行引号/编码问题）。"""
import io
import subprocess
import sys

CASE = (
    '队列 8 · 设计期望值 checks 维度（2026-09-16 12:21）：载体页 __measure-quote-setup.html 由 284 行旧体例重写为 430 宽 iframe + '
    '**272 条 checks**（want = page-9 design.tree.json 声明值 + text-fields.py 全字段 + 设计 PNG 430×1211 像素实测）· '
    '红基线（git stash 复现修复前源码、同一份探针两轮）**53/272**、docH 1202 → 绿 **0/272**、docH **1212**（设计帧 1211）· '
    '两轮独立测量 33/33 字段全等 · git stash pop 复位后复跑同值 · 修掉 12 类偏差（卡片/底栏/保存按钮投影 · 三处 0.8 描边 border→box-shadow · '
    '字数提示行框 16→15 · 凭证说明图标盒 20×20→14×18 · 模型工具栏 40→44 · 模型行高 58→59 · 底部说明 padding 12→16 且图标盒 13→15×20 · '
    '提示卡文案行距 16→14 使卡高 56→52 · 12 处图标盒按设计图层且形状移入 ::before · 返回/帮助圆角 50%→18px）· '
    '交互相 ?scenario=actions 两轮逐字节相同：勾选第 4 行/全选/全不选 计数 3→4→5→0 · 保存 → 真实 POST /quotes + POST /quotes/q9/items → '
    'toast「保存成功」→ /pages/model-pricing/index?quoteId=q9 · 纯测量轮 serve 实收仅 3 行（profile + credentials + credentials/c1）· '
    '像素对账（实现截图 vs 设计 PNG）内容列 49/49 + 条列 19/19 = **68/68 命中、未命中 0** · '
    '证据：evidence/review-序号9-checks-报告.md · red/green-序号9-checks-*.txt · green-序号9-checks-交互回放.txt · cmp-序号9-checks-两轮.txt · '
    'cmp-序号9-设计PNGvs实现截图-结构带.txt · review-序号9-checks-{red-,actions-}run{1,2}.json · requests-序号9-checks-*.txt · '
    '截图 evidence/20260916-1221-序号9-模型报价设置-checks轮-h5-430宽.png（build:mp-weixin / build:h5 / type-check / npm test 1172×2 同轮通过）'
)

NOTE = (
    '队列 8 · 序号 9 checks 轮的口径纠正与留痕：①状态文件在办项曾把本行写成「→ /pages/model-pricing/index，载体页 __measure-model-pricing.html」，'
    '与台账「目标路由 = /pages/quote-models/index」及仓库实际不符（/pages/model-pricing/index 是**序号 11**）→ 本轮按台账执行并在状态文件改正；'
    '②设计稿静态假数据：字数提示写「13/30」，而同一帧的名称文案「2024Q3 主线路报价」只有 **12** 字（同族于决策 D3 的图例百分比）→ '
    '实现按真实字数计算（12/30），探针只断言「格式 + 与名称长度一致」，设计字面量登记在 designLiteralDiff 字段，**不照抄**；'
    '③本页定标的设计模型（可复用于同族表单页）：CJK 文本行框 = fontSize×1.4 取整（15→20 · 14→19 · 13→18 · 12→16 · 11→15，**设计显式 height 优先**）· '
    'remixicon 字形行框 = fontSize×1.5（20→30 · 18→27 · 16→24 · 13→20 · 12→18 · 11→17）· stroke{align:center,thickness:0.8} → '
    'box-shadow 0 0 0 .8px（**实测 Chrome 对 box-shadow 的 used 值保留 0.8px 不取整**，旧口径「取整成 1px」只对 border 成立）· '
    'effects.drop_shadow → box-shadow（卡片 (0,4,16,rgba(15,23,42,.06)) · 底栏 (0,-4,16,rgba(15,23,42,.05)) · 保存按钮 (0,6,16,rgba(37,99,235,.28))）；'
    '④原列的 11 条待拍板缺口沿用（本轮不新增、不擅自改设计稿口径）。'
)

subprocess.check_call([sys.executable, '.agents/state/append-ledger-note.py', '9', '--case', CASE, '--note', NOTE])
subprocess.check_call([sys.executable, '.agents/state/normalize-ledger-eol.py'])
print('done')
