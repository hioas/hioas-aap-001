# 序号 4-v1「接入凭证-表单」设计期望值 checks 轮报告

- 轮次：`aap-tdd-run-20260916-1005`（cron `*/5`）· 2026-09-16 10:05~10:35
- 页面：`/pages/credential-submit/form`（帧「24. 报价端·小程序 ｜ 接入凭证-表单」，frame `layer_id cb1de468-0658-4ccb-a1c3-46c2f48f6314`，抓取 id `page-24`，430 宽）
- 队列：队列 8「给载体页补设计期望值 checks 维度」第 3 页（序号 3 → 序号 4 → **4-v1**）

## 1. 设计真源与帧引用（先重抓、再对账）

- 重抓命令：`python C:/Users/laitz/AppData/Local/hermes/skills/calicat/scripts/calicat_source.py page --url https://www.calicat.cn/design/2095515676955668480 --layer-id cb1de468-... --page-id page-24 --out "$LOCALAPPDATA/Temp/aap-live"`
- 结果：`design.json` sha256 `bd2498588806682448bd30b661ac10d9166270f06322c30ab28597b3479acc7e` 与仓库留证**逐字节相同** → 画布当前状态 = 实现所依据的版本，**无漂移**。

## 2. 设计期望值的两类来源（want 不许目测）

1. **声明值**：`.calicat/raw/pages/page-24/design.tree.json` + `python .agents/state/dump-node-fields.py page-24 <节点名>`
   （padding / gap / 固定宽高 / cornerRadius / stroke.thickness / effects / fontSize / fontFamily / 文案）。
2. **fit_content 行的真实行框**：设计 PNG 色带实测
   `curl -o design24.png https://prototype-prod-1254106194.cos.ap-beijing.myqcloud.com/calicat/file/2099902651224866816/canvas/image/2099902651224866816.png`
   - `png-rows.py design24.png v 30 0 1200 1` → 顶部栏 74（+1px 分隔影）· 卡 90..477 / 494..591 / 608..881 / 898..1015
   - `png-rows.py design24.png v 100 88 1137 2` → 输入框 166/250/334/418（各 44）· chip 542..575（34）· 备注框 945..998（56）· 按钮 1032..1079（48）
   - `png-rows.py design24.png h 558 30 400 3` → 三个 chip 各 77 宽 @x36/121/206
   - `png-rows.py design24.png h 655 30 400 2` → 上传区描边**连续 334px**（实线，不是 dashed）
- **关键模型（本轮定标）**：fit_content 文本行的真实行框 ≈ 字号度量行框 —— 实测 18px→24 · 14px→20 · 13px→20 · 12px→18 · 11px→16；
  图标字形行框 = fontSize×1.5（24→36 / 22→33 / 20→30 / 18→27 / 14→21，与序号 4 的结论一致）。

## 3. 红 → 绿（同一份探针，两态各跑两轮）

| | checkCount | checkFailCount | docScrollHeight |
|---|---|---|---|
| phase1 空态（修复前 / 后） | 6 | **5 → 0** | 1019 → **1071**（= 1137 - 54 - 12） |
| phase2 已上传态（修复前 / 后） | 249 | **78 → 0** | 1079 → **1137**（= 设计帧高） |

- 红基线复现方式：`git stash push -- aap-client/src/pages/credential-submit/form.vue` → `npm run build:h5` → 跑探针；
  证据 `evidence/red-序号4v1-checks-设计期望值偏差.txt`（78 条逐条转录）、`evidence/review-序号4v1-red-run{1,2}.json`。
- 绿证据：`evidence/review-序号4v1-run{1,2}.json`（两轮独立测量 **33/33 字段全等、不一致 0**）、
  `review-序号4v1-final-run{1,2}.json`（stash 复位后复跑，同样 0 偏差且与首轮逐字段相同 → 证明复位干净）。
- 红/绿逐字段差异：`evidence/cmp-序号4v1-红vs绿.txt`。
- 探针初版红基线为 80 条，其中 3 条是本轮**探针自身**口径错误（见 §6），修正后定稿 78 条。

## 4. 修掉的 9 类设计偏差（`aap-client/src/pages/credential-submit/form.vue`）

| # | 偏差 | 设计依据 | 修前 → 修后 |
|---|---|---|---|
| 1 | 顶部栏高 | 顶部栏 padding 16/16 + 标题块 24+18（声明 height）= 42 > 返回按钮 36 | 68 → **74**；返回/扫描按钮垂直中心 34 → **37** |
| 2 | 7 个图标占位盒尺寸 | 各图层 `width` + `fontSize`（行框 ×1.5） | 返回 16×16→**20×27** · 扫描 16×16→**20×27** · 上传云 22×22→**24×33** · 文件 15×18→**22×30** · 删除 20×20→**20×27** · 提交勾 11×11→**22×30** · 脚注盾 12×12→**16×21**（形状全部移入 `::before`） |
| 3 | 13 处字重 | `fontFamily`：Bold→700 · SemiBold→600 · Medium→500 · Regular→400 | 标题 600→**700**；卡标题 600→**700**；字段标签 400→**600**；chip 文字 400→**600**；上传主文案 400→**600**；文件名 400→**600** |
| 4 | 文本行高（卡高全短） | 设计实测行框 18/20/16/20 | 全站 `line-height:1.2` → 12px **18** · 13px **20** · 11px **16** · 14px **20** · 18px **24** |
| 5 | 输入框/chip/备注框描边 | `stroke{align:center, thickness:0.8}` | `border:1px` → `box-shadow: 0 0 0 0.8px`（border 占布局：内容宽 356→**358**、输入文本 49→**48**）；选中 chip 无描边（设计只有 fills） |
| 6 | 上传区线型 | `stroke` 无 dash + PNG 行 655 连续 334px | `1px dashed` → **实线 0.8px** box-shadow |
| 7 | 备注框高 | padding 12/12/24/12 + 文本行框 20 | 52 → **56**（textarea 28 → **20**，padding-bottom 24） |
| 8 | 已上传文件行高 | 名称 12px/行框 18 + 大小 11px/行框 16 = 34 | 48 → **54** |
| 9 | 卡高/卡位 | 上述 1~8 的合力 | 370/93/259/111 → **388/98/274/118**；卡 top 84/470/580/855 → **90/494/608/898** |

## 5. 像素级对账（实现截图 vs 设计 PNG，同一列逐带对比）

`evidence/cmp-序号4v1-设计PNGvs实现截图-色带.txt`（x=30 与 x=100 两列）：设计 91..476 / 495..590 / 609..880 / 899..1014 / 按钮 1033..1078
vs 实现 91..475 / 495..589 / 609..879 / 899..1013 / 按钮 1033..1078 —— **逐带相同**（±1px 为抗锯齿半带）。
顶部栏三条带（0..19 白 / 21..52 返回圆 #F1F5F9 / 54..73 白）+ 页底色从 75 起，两图完全一致。

## 6. 探针/工具侧本轮自纠（都不是页面缺陷）

1. `declared(sel, prop)` 传 `[data-testid=...]` 选择器取不到样式表声明值（CSS 里是类名选择器）→ 用类名。
2. Chrome 把 `box-shadow` **声明值**序列化成 `rgb(238, 242, 247) 0px 0px 0px 0.8px`（颜色在前、逗号后带空格）→ 新增 `declaredNorm()` 归一化空白再比。
3. **uni-app H5 的 placeholder 不是 attribute**：`<uni-input>` 内部渲染 `.uni-input-placeholder` 文本节点 → 改写 `placeholders` / `remarkPlaceholder` 为断言渲染文案（更接近用户所见），并在快照里留 `placeholderDebug` 供下次诊断。
4. chip 左边界/宽度是**文字驱动**（设计 49px 字宽来自 SourceHanSans，H5 不加载该字体）→ 改 ±3 容差断言 `chkNear`，容差写进 check key。
5. 取数用 iframe 900 高（页面 `min-height:100vh` 会把 scrollHeight 顶成视口高）→ 截图走 `?shot=1`（1200 高，且停在已上传态不跳页）。

## 7. 交互相与「有牙齿」的证据

- phase3 `?scenario=guard`：点 chip（client-only）+ 空表单提交 → toast「请输入客户名称」、hash 未变、文件行仍在；
  **serve 实收 0 行 /api 请求**（`evidence/requests-序号4v1-guard-run{1,2}.txt` 均 0 行）→ 证明校验门没有偷偷发请求。
- phase4 补必填后提交：真实 `POST /api/v1/provider/qualifications`（body 带 4 个字段 + `qualification_files`，见 `requests-序号4v1-run1.txt`）
  → mock 返回 `detection_job_id=j1` → 跳 `/pages/detecting/index?jobId=j1`（该页 fixture 齐全，落点是活页）。
- mock 缺口先红后绿：`api/v1/provider/qualifications/post` 缺失时 **serve.py 对未定义 POST 会返回 200 `{"id":"c1"}`**（静默假成功，不去看 fixture 就发现不了）
  → `check-mock-fixtures.py` 新增该条（红 FAIL 1 `缺键 detection_job_id`）→ 补 fixture → FAIL 0。

## 8. 质量门与产物

- `npm test` **1168/1168 · 72 files 连跑两轮**（`evidence/green-序号4v1-全量轮{1,2}.txt`）
- `npm run type-check` exit **0** · `npm run build:mp-weixin` exit **0**（`dist/build/mp-weixin/pages/credential-submit/form.{js,json,wxml,wxss}`；
  wxss 含 `box-shadow:0 0 0 .8px #eef2f7|#cbd5e1` · `line-height:20px/18px/16px` · `font-weight:700/600` · `padding:12px 12px 24px` · `width:20px;height:27px` 等本轮设计值）
- `npm run build:h5` DONE · `review-artifacts.py` 22/22 路由三件套齐备且注册
- 430 宽截图：`.agents/state/evidence/20260916-1022-序号4v1-接入凭证表单-checks轮-h5-430宽.png`（另存 `logs/screenshots/` 同文件名）
- 本机未装微信开发者工具 → 真机/开发者工具验收仍留给人类（导入 `dist/build/mp-weixin`）。

## 9. 下一轮

队列 8 第 4 页：**序号 5**（page-5-2「检测进行中」→ `/pages/detecting/index`，载体页 `__measure-detecting.html`，mock 目录 `api`）。
