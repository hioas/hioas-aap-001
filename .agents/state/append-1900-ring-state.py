# -*- coding: utf-8 -*-
"""append-1900-ring-state.py — 状态文件回写（本轮序号 1 center 描边→ring / 图标盒 / effects）。

用法: python .agents/state/append-1900-ring-state.py
"""
import io

P = 'E:/workspaces/hioas/hioas-aap-001/.agents/state/aap-tdd-state.md'

NEW_STATUS = (
    'STATUS: RUNNING — 报价端小程序 22 页已全部实现（台账待取件 0）。当前在办：'
    '①新维度「设计文本叶子 ↔ 实现 DOM」全量审计 ✅（22/22 页 · 1131 设计叶子 · 匹配 970 · 待判读 class 172 → 序号 8 四类经 PNG 判定为非偏差）'
    '②序号 1 登录页四轮收口 ✅（字重 10 处 + 行盒 10 处 · 16px 残差 6 类 · **本轮 5 处 center 描边→ring + 3 个输入框图标盒 20×27 + 设计 effects 两处投影**）'
    '：载体页 checks 133 → **165**（+phase5 勾选态 5 条），红基线 34/163 与 2/165 → 绿 **0/165 · 0/5**，docH 1114 = 设计帧高，'
    '像素对账未命中由 6 条降到 **2 条**（均为设计导出图软染色 2/255）。'
    '③**下轮第一件事 = 按 172 条待判读清单逐页推进（一页一轮）**：'
    '`python .agents/state/textleaf-audit.py --out …` 出当前清单 → 挑未判读 class 最多的一页，按本页同法（want = 设计声明值/PNG 实测 · 先红后绿 · 两轮 + 像素对账）修偏差或登记「已核定(非偏差)」到 `textleaf-accept.json`；'
    '其后依次 队列 1 逐页复核余项、队列 3 的 15 条待人类拍板（只做可自主部分，保持原样等拍板）。队列 0 挂起（D6）；管理端 8 页范围外。'
)

ROUND = '''
- 2026-09-16 19:0x（cron 轮 `aap-tdd-run-20260916-1900`）· **序号 1 两个待办收口（5 处 center 描边→ring · 3 个输入框图标盒 20×27）+ 新发现并修掉设计 effects 缺失（卡片/主按钮投影）—— 载体页 checks 133→165 条 · 红 34/163 与 2/165 → 绿 0/165 · 0/5 · 像素未命中 6→2**：
  ①**TDD 红→绿（本轮主交付，分两段红基线、同一份最终版探针两轮）**：
  RED①（源码未改）**34/163**（`evidence/review-序号1-ringred-run{1,2}.json`，两轮红清单逐条相同）→
  RED②（补 2 条 effects checks）**2/165**（`review-序号1-effred-run{1,2}.json`）→ 绿 **0/165 · phase5 0/5**
  （`review-序号1-final-run{1,2}.json`）；两轮独立测量 phase1 **42/42 字段全等** · `docH 1114` = 设计帧高 · 溢出 0 · 文案缺失 0。
  ②**5 处 Figma `stroke{align:center,thickness:1}` 由 `border` 改 `box-shadow: 0 0 0 1px`**（设计 center 描边不占布局）：
  `.field__box`×3（0969fe4e/4b7f22fc/1b3579fd rgba(226,232,240,1)）· `.captcha`（1bb97e22 rgba(224,231,255,1)）·
  `.sms-btn`（b4fa89d5 rgba(191,219,254,1)）· `.wechat`（6cf8d63a rgba(187,247,208,1)）· `.agree__box`（927a3b46 选中态 fill-only 无描边 →
  未选中用 ring、选中 `box-shadow:none` + `background:#2563EB`，phase5 实测 `{bg: rgb(37,99,235), shadow: none, borderWidth: 0px}`）。
  实测：输入框内容左界 **49→48**（设计 48、右界 381→**382**）· 验证码块与获取验证码按钮左界 **269→270**（设计 270）。
  ③**3 个输入框图标字形盒 16×16 → 20×27**（设计 df37d41e/930dc950/c59ce992 = `w=20 fs=18 remixicon fill=rgba(148,163,184,1)`；
  盒 = 声明宽 × 字号×1.5，形状按设计 PNG 墨迹入 `::before`：手机 11×16 · 盾 15×17 · 锁 15×17 · 2px 描边灰）→
  占位文本左界 **73→76**（设计 76 = 48+20+8）· 手机号输入框左界 **123→119**（竖分隔两侧 spacer 8/8，修前 token `$gap-md=12`）·
  `+86` 固定 `width:25px`（设计 c825d0d3 声明宽 25，PNG 墨迹 x76..99）。
  ④**设计 effects 缺失（本轮像素对账抓出，非样式猜测）**：表单卡片 `cab5940c` `drop_shadow(0,8,24,rgba(15,23,42,.08))` →
  卡底 y891..911 设计 235→248 渐变、修前实现恒 `248,250,252`；主按钮 `7e26d478` `drop_shadow(0,8,20,rgba(37,99,235,.28))` →
  按钮下 y721..740 设计 `(207,221,250)→(247,249,254)`、修前实现恒 `255,255,255`。补 `box-shadow` 后逐值对齐（±1）。
  ⑤**像素对账**（设计 PNG 430×1114 vs 实现截图 430×1114，`cmp-bands-6` ±3）：内容列 **命中 27 / 未命中 2**（修前 25/4）· 条列 19/0；
  未命中仅 y914/920 = 设计导出图软染色（253 vs 255）→ 非页面缺陷；行内墨迹段 手机号行 设计 `52..62/76..99/109..110/119..202` =
  实现 `53..63/76..99/109..110/119..202`（图标 ±1 = 亚像素取整），验证码/短信行文本 `76..159`/`76..187` 逐值相同。
  ⑥**质量门**：`npm test` **1182/1182 · 72 files 连跑两轮**（19:08:34 / 19:09:23）· `type-check` exit 0 · `build:mp-weixin` DONE
  （wxss 含 `box-shadow:0 0 0 1px #e2e8f0`×2 / `#e0e7ff` / `#bfdbfe` / `#bbf7d0` · `border:2px solid #94a3b8` · `width:20px;height:27px`×2 ·
  `width:25px` · `box-shadow:0 8px 24px rgba(15,23,42,.08)` · `box-shadow:0 8px 20px rgba(37,99,235,.28)`）· `build:h5` DONE ·
  `review-artifacts` 22/22 · `check-mock-fixtures --mock api` FAIL 0。
  ⑦**证据**：`evidence/redgreen-序号1-ring图标盒投影-20260916.txt` · `evidence/review-序号1-ring-icon-checks-报告.md` ·
  `evidence/review-序号1-{ringred,effred,final}-run{1,2}.json` · 截图 `evidence/20260916-1930-序01-登录注册-ring图标盒投影-h5-430宽.png`（430×1114）。
'''

TOOLS = '''
### 5.20 本轮（19:0x 轮 · 序号 1 ring/图标盒/effects）新增的工具与口径

- **设计声明值逐页转储**：`python .agents/state/dump-1-decl.py <pageId> [--grep 关键词]` —— 打印设计树每个节点的
  `id|type|name| w/h · fs · 字体 · 行高 · 填充 · 描边(含 align/thickness) · effects · 文本`，是「want 取声明值」的第一手尺子
  （本轮凭它一眼取到 3 个输入框的 `stroke{align:center}`、3 个图标字形层的 `w=20 fs=18 fill=灰`、卡/按钮的 `effects`）。
- **字形形状判定**：`python .agents/state/ink-rowwidth.py <png> <x0,y0,x1,y1> [...]` —— 逐行打印墨迹 x 段，
  一眼分清「描边字形（两侧窄段 + 尖/圆收口）」与「填充字形」（本轮三个输入框图标全为**描边**字形：手机 11×16 圆角矩形 + 内点、
  盾 15×17 尖底、锁 15×17 锁体 + 锁梁）。
- ⚠️ **`rects()` 的键是 `x` 不是 `left`**：`__measure-login.html` 的 `rects()` 返回 `{x,top,right,bottom,w,h}`，
  用 `r.left` 聚合会得到 `undefined` → `join(',')` 变成 `",,"`，看起来像「页面全错」其实是探针 bug（本轮 2 条假红）。
  用 `rectFor()`（裸 DOMRect，有 `.left`）时才写 `left`。
- ⚠️ **apply 脚本的分段执行会重复插入**：`apply-*.py` 只校验「锚点唯一」，先 `--probe-only` 再整跑 → 同一段 checks 插两次
  （本轮实测 checks 165→167、同名 check 两条）。凡分两段跑，落盘后必须 `grep -c "chk('<key>'"` 复核为 1（或把脚本做成幂等）。
- ⚠️ **带 alpha 的投影色不能用 `ringColor()` 归一化**（它会把 alpha 丢掉）：投影一律整串比对
  `g('sel','boxShadow') === 'rgba(15, 23, 42, 0.08) 0px 8px 24px 0px'`（Chrome 序列化：色在前 + 尾随 spread `0px`）。
- ⚠️ **`stroke{align:center}` 的实现差异只在「内容盒」上显形**：`.agree__box` 这类固定 18×18 的盒子换 ring 后外框不变，
  探针必须去测**内容左界**（`.field__box` 内首个子元素 x）或**相邻元素 x**（`prefix.left` / `divider.left` / `input.lefts`），
  这才是「border 占布局」的可测证据。
- ⚠️ **设计 effects 缺失只能靠像素抓**：载体页若没有 shadow 类 checks，几何全绿也漏（本轮卡片/主按钮投影缺失 20 多轮无人发现）
  → 每页收口时必须把该帧 `design.tree.json` 里所有 `effects` 转成 checks（本轮 2 处）。
- **本轮新增脚本**：`dump-1-decl.py` · `ink-rowwidth.py` · `apply-1-ring-icon.py` · `fix-1-probe-left.py` ·
  `apply-1-ring-icon-src.py` · `apply-1-effects.py` · `gen-1-ring-evidence.sh` · `append-1900-ring-note.py` · `append-1900-ring-state.py`。
'''

raw = io.open(P, encoding='utf-8', newline='').read()
lines = raw.split('\r\n')
assert lines[0].startswith('STATUS:')
lines[0] = NEW_STATUS
out = '\r\n'.join(lines)
if not out.endswith('\r\n'):
    out += '\r\n'
out = out.rstrip('\r\n') + '\r\n' + ROUND + TOOLS
io.open(P, 'w', encoding='utf-8', newline='').write(out)
print('STATUS 行已更新；追加本轮小结 %d 字' % (len(ROUND) + len(TOOLS)))
print(out.split('\r\n')[0][:100])
