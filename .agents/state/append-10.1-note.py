# -*- coding: utf-8 -*-
"""序号 10.1 checks 轮的台账追加（长文本走文件，避免命令行引号/编码问题）。"""
import subprocess
import sys

CASE = (
    '队列 8 · 设计期望值 checks 维度（2026-09-16 13:0x）：载体页 __measure-profile.html 由 314 行旧体例重写为 430 宽 iframe + '
    '**271 条 checks**（want = page-10-1-2 design.tree.json 声明值 + text-fields.py 全部 58 个文本叶子 + 设计 PNG 430×1414 像素实测：'
    'png-rowmodal / text-rows / ink-bbox / ink-runs / scan-row / scan-col）· 红基线（修复前源码 + 同一份探针两轮）**22/271**、docH 1414 → '
    '绿 **0/271** · 两轮独立测量 **43/43 字段全等** · 修掉 3 类偏差（①8 处图标占位盒按设计图层：胶囊 15×20 · 卡头 20×27 ×3 · 锁定 14×18 · '
    '文档 26×36 · 上传 22×30 · chevron 22×30，形状移入 ::before；②2 处 Figma center 描边 border→box-shadow 0 0 0 1px（上传按钮 #93C5FD / '
    '保存按钮 #CBD5E1）；③胶囊宽 91→95 且 x 323→321）· 交互相两轮逐字节相同：保存 → 真实 **PUT /api/v1/provider/profile**（serve 实收 body 见 evidence）'
    ' → toast「保存成功」+ 完整度 72%→**78%**（pill/percent/bar `width:78%` 三处一致）· 四个入口（编辑/管理/上传新资质/去补全资质）均跳 '
    '`/pages/profile-edit/index` · 返回 = navigateBack（hash 不变，直进无栈）· 每轮 serve 实收 24 行 = **1 条写请求 + 11 对只读 GET** · '
    '像素对账（实现截图 vs 设计 PNG 文本带，按最近 y0 一对一匹配、不按 index）**命中 31/33 = 97%**（唯一未命中 = 官网值行被设计切成 h11 + h1(602) 两条带）· '
    '证据 evidence/review-序号10.1-checks-报告.md · red/green-序号10.1-checks-设计期望值*.txt · green-序号10.1-checks-交互回放.txt · '
    'cmp-序号10.1-设计PNGvs实现截图-文本带.txt · review-序号10.1-checks-{red-,}run{1,2}.json · requests-序号10.1-checks-run{1,2}.txt · '
    '截图 logs/screenshots/20260916-1309-序号10.1-供应商档案-checks轮-h5-430宽.png（430×1414 = 设计尺寸）· 质量门 npm test **1173/1173 连跑两轮** · '
    'type-check exit 0 · build:mp-weixin 产物 pages/profile/index.{js,json,wxml,wxss} · build:h5 DONE · 设计帧重抓 sha256 逐字节相同（无漂移）'
)

NOTE = (
    '队列 8 · 序号 10.1 checks 轮的口径与残差登记：'
    '①探针工具本轮新增 5 把尺子（node-by-id.py 按 layer_id 查声明值 · ink-bbox.py 区域墨迹包围盒 · ink-runs.py y 带内 x 向墨迹段 · '
    'scan-row.py / scan-col.py 单行/单列颜色分段），并修正 4 处**探针自身**口径错误（`A@@N B` 型选择器被 list 助手当成「全部 A 的文本」→ '
    '新增 resolveAll() · padLeft 误用 rect 检查 · 资质角标 top 目测值错（PNG 实测 1072/1136）· `.qual-row__info` 的盒 x 是 padding 外层 84 而非内容 96）；'
    '②图标占位盒口径沿用序号 10：盒 = 设计图层宽 × fontSize×1.5，形状入 ::before（本页 6 类 8 处）；'
    '③Figma stroke{align:center,thickness:1} → box-shadow 0 0 0 1px（本页 2 处按钮）；border 会把 193 宽按钮的内容压成 191；'
    '④**残差（未擅自改设计稿）**：卡2 高 414 vs 设计 413（设计卡2 底部 padding 只有 19 行、与 padding:20 的 auto-layout 不自洽 → 实现按 20 落地，'
    '整页仍 1414 = 设计帧高）· 简介两行墨迹行距 设计 15（918..928/933..943）vs 实现 20（916..926/936..946）= 设计自身声明 height=40 与墨迹行距不自洽，'
    '实现按声明盒高落地（盒 899..962 = 64 与设计逐值相同）· 占位图形墨迹 head 18×18 vs remixicon ink 17×16、文档 20×22 vs ink 19×21（决策 D5）；'
    '⑤顺带修工具卫生：`check-mock-fixtures.py` 默认模式把 api-11 的路径打到 api 目录上 → **永久假 FAIL**，已改为「按每条 check 自带的 mock 目录分组、'
    '各起一次 serve」（2 组 FAIL 0），变体目录前缀继承规则收窄为「仅当请求目录不是已注册分组」（api-tmp-* 仍继承、api-11 不再误继承）；'
    '⑥原列 11 条待拍板缺口沿用，本轮不新增、不擅自改设计稿口径。'
)

subprocess.check_call([sys.executable, '.agents/state/append-ledger-note.py', '10.1', '--case', CASE, '--note', NOTE])
subprocess.check_call([sys.executable, '.agents/state/normalize-ledger-eol.py'])
print('done')
