# aap-admin 页 4 / 5 / 8 实现报告（page-4-pc · page-5-pc · page-8-pc-new-api）

> 轮次：2026-09-19 夜（前台会话）· 顺序依据 `design-source-web-frontend` 技能铁律「逐页按设计源页码前缀顺序」。
> 三页原先都是 39 行骨架（带「待实现」徽章），本轮按设计真源实现并接入既有后端接口。

## 一、结论速览

| 页 | 设计真源 | 状态 | 真实数据来源 | 未覆盖部分（已登记） |
|---|---|---|---|---|
| 4 供应商管理 | `page-4-pc` + 抽屉 `page-4-1` | ✅ 已实现 | `GET /admin/providers`（实测 7 条）· `POST /admin/providers/{id}/suspend|resume` | 「接入线路」列无字段；催办/催签/看报告无管理端接口；**新增供应商无接口**（D-ADM-4） |
| 5 检测中心 | `page-5-pc` | ✅ 已实现（含显式缺口） | `POST /detection-jobs/{id}/release`（DET-06）· `ADM-CFG01…05` 检测配置 | **任务监控无列表接口** → 四项 KPI 与任务表渲染为未知（D-ADM-5） |
| 8 new-api 同步 | `page-8-pc-new-api` | ✅ 已实现 | `ADM-S01/04` 任务与渠道绑定 · `ADM-S03` 重试 · `ADM-S05` 启停 · `ADM-S06` 上游清单 | 立即同步 / 自动同步 / 下次同步 / 同步间隔无接口（D-ADM-6）；渠道行「同步价格」无字段 |

## 二、真实执行证据

### 1) 单元/契约测试（aap-admin）

```
npm test（含 CSS 注释门禁）连跑两轮：
  run1  Test Files 5 passed (5)   Tests 52 passed (52)
  run2  Test Files 5 passed (5)   Tests 52 passed (52)
type-check（vue-tsc --noEmit）：exit 0（无输出）
CSS 门禁：✓ 扫描 29 个文件，无提前终止
```

新增 3 个测试文件（34 条）：`tests/unit/providers.spec.ts`(18) · `detection.spec.ts`(6) · `sync.spec.ts`(5) + 既有 23 条 → 52 条。

### 2) 有头真实浏览器验收（本地 Chrome，`tools/admin-acceptance.mjs`）

```
管理端联调：通过 15，失败 0        （9 个路由 + 登录/验证码/样式门禁）
  ✓ /providers  供应商管理 — 业务内容已渲染；接口 1 次，控制台 0 报错
  ✓ /detection  检测中心   — 业务内容已渲染；接口 1 次，控制台 0 报错
  ✓ /sync       new-api 同步 — 业务内容已渲染；接口 4 次（含已声明放行 E-1501），控制台 0 报错
真实 HTTP 31 次。
```

证据落地位置（`aap-admin/evidence/` 被 `aap-admin/.gitignore` 忽略，故**另存一份可入库的 JSON**）：

| 内容 | 路径 | 是否入库 |
|---|---|---|
| 验收明细（15 行判据 + 31 次真实 HTTP 流水） | `.agents/state/evidence/adm-acceptance-20260919.json` | ✅ 入库 |
| 原始 JSON 与三页截图 | `aap-admin/evidence/admin/{admin-acceptance.json,page-providers.png,page-detection.png,page-sync.png}` | ❌ 本地（目录被 gitignore，沿用既有约定） |

三页的验收判据已写进 `CONTENT_GATES`（并要求「文案形态」命中，例如 `共 \d+ 家`、`共 \d+ 条，每页 \d+ 条`），
骨架页不可能通过；`/sync` 声明式放行 `E-1501`（未配置 ACTIVE new-api 端点的已知形态），其它错误码仍会失败。

## 三、本轮查出的真缺陷（非前端能绕）
### 缺陷8 · 管理端分页参数名不匹配 → 后端静默降级为默认 20 条/页

- 现象：`aap-admin` 各 api 模块发 `page_size`，后端 `@RequestParam(required = false) Integer pageSize` 绑不上 →
  **静默**用默认 20。请求 100 / 200 / 500 条也只回 20 条。
- 影响：仪表盘 KPI（请求 100 条）、用量页（请求 500 条）等**统计口径被截断**，且没有任何报错 ——
  典型「假绿」：接口 code=0、页面照常渲染，数字却是错的。
- 实证：`.agents/state/evidence/redgreen-defect8-pageSize.txt`

```
/admin/providers?page=1&pageSize=3    → 服务端 pageSize=3   items=3
/admin/providers?page=1&page_size=3   → 服务端 pageSize=20  items=7   ← 参数被忽略
/admin/audit-logs?page=1&pageSize=2   → 服务端 pageSize=2   items=2   total=157
/admin/audit-logs?page=1&page_size=2  → 服务端 pageSize=20  items=20  total=157
```

- 修复：`providers.ts` / `reviews.ts` / `contracts.ts`(×3) / `usage.ts` / `dashboard/model.ts`(×5) 全部改为 `pageSize`；
  `PageResult` 补 `pageSize?`（响应侧真实字段就是驼峰）；`reviews` 页对 `/quotes/{id}/items` 去掉无效分页参数（该端点无分页）。
- 回归判据：`providers.spec.ts`「分页参数名是 pageSize（不是 page_size）」，**先红后绿**实测
  （`tools/redgreen-defect8.sh`，RED exit=1 / GREEN exit=0）：`.agents/state/evidence/redgreen-defect8-vitest.txt`
- 修复后实测流水（同一次验收）：`/admin/providers?page=1&pageSize=100`、`/admin/usage/hourly?…&pageSize=500` 等均已生效。

### 附带修掉的控制台噪声

`index.html` 无 favicon → 浏览器默认请求 `/favicon.ico` 得 404，控制台留一条
`Failed to load resource: 404`，会污染「控制台 0 报错」这条验收判据。已加内联空 favicon。

### 缺陷11 · 证据文件把**真实令牌**写进 git（本轮自查发现，已修复）

- 两个验收脚本把后端响应体原样写进证据 JSON，`/auth/sms/login` 的响应含**真实 access token
  （303/307 字符 JWT）与 refresh token（43 字符）**：`aap-client/evidence/h5-chain/h5-chain-result.json`
  **已入库**（历史仍有），`aap-admin/evidence/admin/admin-acceptance.json` 本轮新产出。
- **为什么人眼自检拦不住**：工具输出层会把 JWT 打码显示成 `eyJhbG...xxxx` —— 看日志/看 diff 都会
  以为「已经脱敏了」。所以守卫必须是**机器判据 + 落在写文件那一步**。
- 修复：两个脚本写文件前机器脱敏（白名单键名 + 真 JWT 形状 → `<redacted len=N>`，保留长度）；
  新增共享守卫 `tools/evidence-secrets.py`（扫描命中即 exit 1 / `--redact` 就地脱敏）；
  已入库的 `h5-chain-result.json` 就地脱敏（纯文本替换，**仅 3 行改动**）。
- 验证：全仓复扫 **0 命中**；重跑一次有头验收后新写 JSON 复扫仍 0 命中（写时脱敏生效）；
  脱敏后 JSON 合法、证据内容不变。
- 踩坑（已回退）：第一版用 `json.load`+`json.dumps` 重写整份文件 → 把他方 6 个证据文件**整份重新格式化**
  （1124 行 diff，会打乱他们的 size+md5 回归守卫），且键名用子串匹配误伤 `tokenPage`。已回退并改为
  纯文本替换 + 白名单精确匹配。
- 残留：旧令牌仍在 git 历史里（dev 环境、TTL 2h）→ 是否重写历史/轮换 dev 密钥**需你拍板**，本轮未动历史。

## 四、设计源内部不一致（登记，不静默二选一）

1. **供应商类型两套措辞**：`page-4-pc` 列表列写「渠道商 / 原厂 / 中转商」，
   `page-4-1` 抽屉写「官方直连 / 第三方代理 / 自建网关」。取值统一为后端枚举
   `ORIGINAL | RESELLER | AGGREGATOR`（`ProviderController` 的 `@Pattern`），两套文案都在代码里留痕，
   页面上可见地说明该偏差。
2. **page-5-pc 的 KPI 与任务表无数据来源**（见 D-ADM-5）：设计稿的 8 / 12 / 46 / 4.2% 是画布示意值，
   本轮**不填充**任何示意数据，KPI 渲染为 `—` 并说明「无列表接口 → 未知（不是 0）」。
3. **page-8-pc 的「同步价格」列**：`ChannelBinding` 无单价字段（价格在报价单/编译产物上）→ 渲染 `—`。

## 五、诚实边界（本轮沿用项目口径）
- 取不到的维度一律 `—`，**不用 0 冒充未知**；每个 `—` 旁边都有可读的原因说明。
- 后端没有的能力**不给假按钮**：新增供应商抽屉（page-4-1）按设计实现完整 UI + 校验错误态，
  保存/保存草稿/测试连通三个动作都明确提示「后端未提供接口 → 本次未发出任何请求」。
- 检测中心把「无列表接口」做成页面顶部可见告警 + 可执行的空态（说清原因与解除路径），
  并把筛选控件显式禁用（避免点了没反应的假筛选）。
- 前端角色过滤只是渲染过滤，三页的代码注释与页面文案都写明后端另有二次校验。

## 六、与他方会话的交汇 & 安全发现

- **缺陷2（文件服务）已由另一会话修复**（`9cf495f`，211/211 全绿）：新增 `POST /api/v1/files`
  （multipart，字段 `file`，可选 `biz_type`）与 `GET /api/v1/files/{id}`。
  管理端「供应商资质文件」「合同文本」两处文案已按事实更新为**代码已就绪**，
  并标注 ⚠️ **当前 dev 实例未重启到该版本 —— 实测 `POST /files` 仍 404 `E-1406`**（重启后再验）。
  管理端仍有一条限制：`POST /provider/qualifications` 仅供应商本人可用（管理端 403 `E-1901`）。
- **`index.html` 的内联空 favicon 由他方会话代为提交**（`e362ac6`，与本轮改动一致）；本轮其余改动在其之上，
  未 rebase / reset / 改写他方提交。
- **S-1 安全发现（静态确证、运行未复现）**：`GET /files/{id}` 无归属校验 —— `SecurityConfig` 只要求
  `authenticated()`，`FileController` 无 `@PreAuthorize`、无归属判断 → 任意已登录角色拿到 `file_id`
  即可下载他人文件（IDOR）。因 dev 实例未重启到含 `FileController` 的构建，**运行层无法实证**，
  只报代码层结论；建议与处置方案见 `.agents/state/aap-decisions.md` S-1。

## 七、待拍板（新增，详见 `.agents/state/aap-decisions.md`）

| 编号 | 事项 | 建议 |
|---|---|---|
| D-ADM-4 | 管理端无「创建供应商」接口（`POST /admin/providers` 不存在） | 若 page-4-1 抽屉要落地，需补后端接口 + 校验规则；否则抽屉保持「UI 完整 + 明确未提交」 |
| D-ADM-5 | 管理端无「检测任务列表」接口 → 任务监控页无数据 | 优先补列表 + 聚合计数（与缺陷1 执行器缺失相关：任务恒 QUEUED，列表价值有限） |
| D-ADM-6 | 无「立即同步 / 同步计划配置」接口 | 补 `POST /admin/sync/tasks`（触发一次同步）与计划配置；否则保持只读 + 按任务重试 |
| 遗留 | D-ADM-2（page-3 智检云孤例是否废弃）、D-ADM-3（模型管理后端能力） | 未变，仍待裁定 |
