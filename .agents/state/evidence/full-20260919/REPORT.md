# 三端全量测试与联调报告

**时间**：2026-09-19 23:34 – 23:47（CST）
**环境**：dev（PG18 `dev_postgres` @WSL docker，库 `aap_server_dev`）
**被测服务**：aap-server `:8084`（IDEA MCP 启动，`AAP_ALLOW_LOOPBACK=true` + `AAP_SMS_EXPOSE_CODE=true`）
**证据目录**：`.agents/state/evidence/full-20260919/`

---

## 一、账号变更：15801818092 → 管理员

| 项 | 值 |
|---|---|
| 账号 id | `458857864037642240` |
| 手机号 | `158****8092`（明文 `15801818092`，用 `sha256(phone)` 与库内 `phone_hash` **精确匹配确认**） |
| 角色变更 | `SUPPLIER` → **`SUPER_ADMIN`** |
| 变更方式 | 直接改 `aap_provider_account.role`（**后端无账号/角色管理接口**，仅有 auth） |

**实测验证**（不是只看库那一行）：

```
POST /auth/sms/send   → code=0, dev_code=123456
POST /auth/sms/login  → code=0, token 签发成功
GET  /auth/me         → role=SUPER_ADMIN, phone_masked=158****8092, providerCode=AAP-P-000007
GET  /admin/reviews   → code=0（仅管理员接口，实测可访问，返回待审池）
```

> 备注：`aap_admin_user` 表存在但**为空**；管理端账号实际以 `aap_provider_account.role` 判定。
> 该表仅被「明文 apikey 二次验证」使用（`CredentialService.requireAdminPhone`），且当前无人绑定手机号
> → 超管走 reveal 会得到 `E-1901 当前管理员未绑定手机号，无法完成二次验证`（已登记为待办）。

---

## 二、三端测试结果

| 端 | 命令 | 结果 |
|---|---|---|
| **server** | `mvn -o test`（注入 `E:/env/aap-server.env`） | **206/206 · BUILD SUCCESS** |
| **aap-client**（H5+小程序，uni-app） | `npm test` + `npm run type-check` | **1234/1234（77 files）** · type-check exit 0 |
| **aap-admin**（Vue3+Vite+Element Plus） | `npm test` + `vue-tsc --noEmit` + CSS 门禁 | **23/23（2 files）** · type-check exit 0 · CSS 门禁通过 |

**aap-admin 原先一条测试都没有**（`No test files found`），本次补齐 23 条：
- `tests/unit/http.spec.ts`（12 条）：统一响应包解析 / 业务码非 0 抛 ApiError / 401 与 E-1902 清 token 登出 /
  `skipAuthRedirect` / **网络层失败与业务失败区分** / 非 JSON 响应 / query 构造（丢空值、数组展开）/
  Authorization 自动附加 / body 序列化 / tokenStore
- `tests/unit/contract-rbac.spec.ts`（11 条）：导航文案逐字对齐设计稿 / **PRD 13 §1 权限差异**（技术运营不能通过报价、
  不能写合同；运营商务不能改检测配置、读审计、配 new-api）/ 驳回原因码**逐字等于后端枚举** / 状态徽章五色 / humanCount / RFC3339

**新测试立刻抓到一个真 bug**：`http.ts` 读的是 `env.trace_id`，而后端统一响应包用的是**驼峰 `traceId`**
→ **追踪号从来没被捕获过**（排障时拿不到）。已修（两种写法都容错）。

---

## 三、联调结果（真实浏览器）

### 3.1 供应商端 H5 链路（有头 CDP，Chrome）

**21/21 通过 · 29 次真实 HTTP · 控制台 0 报错 · exit=0**

```
登录 → 凭证（含模型清单）→ 预检 → 检测 → 报告 → 报价单创建 → 定价 → 预览提交 → 列表
⑲ POST /quotes code=0（id=458944140753375232）；明细写入 code=0
⑳ PUT /quotes/items/{itemId} code=0；体={"input_price":2.5,"output_price":10,"billing_mode":"按 token"}
㉑ POST /quotes/{id}/submit code=0
㉒ 报价单 Q20260919000009 status=SUBMITTED   ← 业务结果断言，非状态码
```

### 3.2 管理端（本地 Chrome · 有头 · Playwright）

**15/15 通过 · 32 次真实 HTTP · 控制台 0 报错 · exit=0**

```
✓ 全局样式（登录页） — --c-page=rgba(241,245,249,1)，body=rgb(241,245,249)/12px
✓ /dashboard 业务内容已渲染；接口 5 次      ✓ /usage  业务内容已渲染；接口 2 次
✓ /models    业务内容已渲染；接口 2 次（含已声明放行 E-1501）
✓ /reviews   业务内容已渲染；接口 4 次      ✓ /contracts 业务内容已渲染；接口 6 次
○ /providers /detection /compilation /sync = 骨架（含「待实现」徽章）
```

### 3.3 跨端链路验证（供应商 → 管理端）

供应商端刚提交的 **`Q20260919000009`**（id `458944140753375232`）**出现在管理端待审池**：

```
GET /admin/reviews?status=PENDING → total=2
  458944224765284352 | quote_id=458944140753375232 | status=PENDING
  458771123234586624 | quote_id=458771030402056192 | status=PENDING
```

---

## 四、保存的测试数据

### 4.1 API 层快照（`data/`，**10/10 资源全部取到**，只读 GET）

| 资源 | total | 文件 |
|---|---|---|
| providers | 7 | `providers.json` |
| reviews-pending | 2 | `reviews-pending.json` |
| reviews-claimed | 0 | `reviews-claimed.json` |
| contracts | 2 | `contracts.json` |
| payments | 0 | `payments.json` |
| settlements | 0 | `settlements.json` |
| sync-tasks | 0 | `sync-tasks.json` |
| channel-bindings | 0 | `channel-bindings.json` |
| usage-hourly | 0 | `usage-hourly.json` |
| audit-logs | 150 | `audit-logs.json` |

另有 `data/summary.json`（含登录身份、各资源 code/total/错误）。

### 4.2 数据库层快照（`db-snapshot.txt`）

**账号与角色（7 个）**

```
458351759960293376 | 138****0827 | SUPPLIER    | ACTIVE
458566994964979712 | 139****0001 | SUPER_ADMIN | ACTIVE
458589637915123712 | 138****8000 | SUPPLIER    | ACTIVE
458691087374704640 | 139****0123 | SUPPLIER    | ACTIVE
458700638073348096 | 135****5000 | SUPPLIER    | ACTIVE
458751692790009856 | 138****8999 | SUPPLIER    | ACTIVE
458857864037642240 | 158****8092 | SUPER_ADMIN | ACTIVE   ← 本次变更
```

**报价单（9 张）**：`Q20260918000001` APPROVED · `Q20260919000002` APPROVED ·
`Q20260919000003`–`Q20260919000007` DRAFT · `Q20260919000008` VOID · **`Q20260919000009` SUBMITTED**（本次新建）

**审核任务（4 个）**：2 个 APPROVED、2 个 PENDING（含本次新建 `458944224765284352`）

**合同（2 份）**：`HT202609180001` CREATED · `HT202609190002` CREATED（**均为 CREATED，未推进**）

**实体计数**：credential 20 · detection_job 20 · report 11 · **file_asset 0** · **payment 0**

---

## 五、缺陷与待裁定（汇总）

### 已修（本轮及前序）

| # | 缺陷 | 状态 |
|---|---|---|
| 4 | `POST /credentials` 未接线 | 已修 |
| 5 | `usage.hourly()` 缺 `from/to` | 已修 |
| 6 | `auth.refresh()` 无页面调用 + 不落盘 | 已修 |
| 7 | H5 `mode="region"` 不渲染（双端不一致） | 已修 |
| 8 | 超长 UA 导致登录 500（微信 UA 279 字符 > varchar(255)） | 已修 |
| 9 | 人工放行不产报告 | 已修 |
| 10 | 前端丢弃预检返回的上游模型清单 | 已修 |
| 11 | `model_list` 形状与契约不符（勾选模型即保存失败） | 已修 |
| 12 | 模型回写带 api_key 把状态打回 | 已修 |
| 13 | 供应商定价页提交仅管理端可写的 `request_rules` | 已修 |
| 14 | **管理端 CSS 注释提前终止 → 设计令牌全丢、页面无样式** | 已修 + 加门禁 |
| 15 | **管理端 `traceId` 字段名读错（排障拿不到追踪号）** | 已修（新测试抓到） |

### 未修 · 需拍板

| # | 缺口 | 证据 | 选项 |
|---|---|---|---|
| **1** | 检测执行器缺失（`recordProbeResults` 全仓零调用方） | 任务永停 QUEUED（靠 DET-06 人工放行绕过） | 补本地最小执行器 / 只出方案 |
| **2** | 文件上传端点缺失（`aap_file_asset` 主代码零 INSERT，实测 0 行） | 合同永停 `CREATED`、签不了、打不了款 | 补 `POST /files` + 存储抽象 / 线下灌入 |
| **3** | 站内信永不产生（`notifyProvider` 唯一调用点在缺陷1 死路径） | 通知表无新记录 | 随缺陷1 一并解决 |
| **D-ADM-2** | 管理端外壳两套口径（`page-3` 是「智检云」孤例，其余 9 页「云算接入」） | 逐页提取 design.json 品牌/用户/导航 | 以多数口径为准（已如此）/ 废弃 page-3 |
| **D-ADM-3** | 模型管理**整页无后端能力**（无 ModelController、无厂商/模型表；唯一只读源实测 E-1501） | 设计稿要的增删改查一个端点都没有 | 补后端 / 降级只读占位 / 暂缓 |
| **D-ADM-1** | 设计稿有「批量通过」，PRD 13 §5 明确禁止 | 已按 PRD 不渲染 + 页面显式提示 | 维持 PRD / 改设计稿 / 折中 |
| **新** | `aap_admin_user` 为空 → 超管 reveal 明文 apikey 会得 `E-1901 未绑定手机号` | `CredentialService.requireAdminPhone` | 给超管绑定 `phone_hash` |
| **新** | 图形验证码后端不校验（`captcha` 无消费处） | 防刷能力为零 | 补校验 |
| **新** | 后端无账号/角色管理接口 | 本次改角色只能直接改库 | 补管理端点 + 审计 |

---

## 六、复现命令

```bash
# server
cd aap-server && set -a && . /e/env/aap-server.env && set +a && mvn -o test

# aap-client
cd aap-client && npm test && npm run type-check

# aap-admin
cd aap-admin && npm test && npx vue-tsc --noEmit && node tools/check-css-comments.mjs

# 联调（真实浏览器，有头）
cd aap-client && AAP_CDP_PORT=9660 node tools/h5-chain.mjs http://localhost:5173 evidence/h5-chain 13800138000
cd aap-admin  && node tools/admin-acceptance.mjs http://127.0.0.1:5174 evidence/admin 13900000001

# 测试数据快照（只读）
cd aap-admin && node tools/snapshot-dev-data.mjs ../.agents/state/evidence/full-20260919/data 13900000001
```
