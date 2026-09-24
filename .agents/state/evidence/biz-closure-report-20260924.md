# 业务闭环端到端交付报告 · 2026-09-24

> 本报告所有读数均来自**本机真实运行**（真实 HTTP、真实浏览器、真实 PostgreSQL），非静态推断。
> 不含任何密钥值；环境变量与凭据仅以变量名引用。

## 结论

「供应商进件 → 档案/凭证 → 检测 → 报价 → 审核/合同签署 → 打款 → 编译验证 → **渠道上架** → 用量回流」
这条业务闭环，**后端链路（T15）与管理端 UI 链路（T16）均已跑通并留有可复现证据**：

运营现在可以在管理端页面上完成
**「登记 new-api 端点 → 发起上架同步 → 执行上架 → 渠道在 new-api 生效」**，
渠道状态经**上游回读比对**确认（`readback=有`），任务终态 `SYNCED`。

---

## 一、本轮新增（T16）：管理端接线

T15 已补齐后端写入侧（ADM-S07/S08/S09），但管理端页面**零调用**这三条端点 ⇒ 运营在界面上既看不到、也点不动。
本轮只做**接线**：不新增端点、不改错误语义、不绕后端闸门。

| 文件 | 改动 |
|---|---|
| `aap-admin/src/api/admin/sync.ts` | `registerEndpoint`(S07) / `createTask`(S08) / `executeTask`(S09) + `NewApiEndpoint` 类型 |
| `aap-admin/src/views/sync/index.vue` | 「发起上架同步」对话框(S08)、「登记同步端点」(S07)、任务行「执行」(S09，二次确认) 与「详情」抽屉(S02) |
| `aap-admin/src/views/usage/index.vue` | 「聚合刷新」按钮(ADM-U02) |
| `aap-admin/src/config/nav.ts` | 新增 `usage.refresh` 权限点（与后端 `@PreAuthorize` 一致） |
| `aap-admin/tools/admin-acceptance.mjs` | 门禁**同步收紧** + 修正两处过期/缺失判据 |
| `aap-admin/tools/publish-e2e.mjs` | **新增**：UI 上架闭环验收 |

### 刻意保留的三条边界（不因「好用」而放宽）

1. **不绕过闸门③**：无 `gate_status=CONFIRMED` 编译产物时后端返回 409 `E-1407`，前端**原样透出**该错误。
2. **Api Key 只进不出**：`api_key` 加密落库，响应只回 `api_key_mask`；页面不回显、失败提示不含 key。
3. **写操作二次确认**：ADM-S09 会真实写入 new-api，点「执行」前必须有确认框。

---

## 二、真实运行证据

### 1. UI 上架闭环 `publish-e2e.mjs` —— 17/17 PASS

| 判据 | 读数 |
|---|---|
| 超管登录 | 第 2 次取码成功（首次 429 属频控，已声明放行） |
| 找到 CONFIRMED 编译产物 | `compilation_id=460730980586139648` |
| 打开「发起上架同步」对话框 | PASS |
| 供应商下拉选中 | `闭环验收科技有限公司` |
| 填写表单 | `channel_name=AAP-UI-1790260291019` |
| **ADM-S08 发起上架同步** | `POST /admin/sync/tasks → 200 code=0` |
| 拿到任务号 | `task_no=SY202609240008 task_id=7` |
| 任务表出现新建任务行 | 匹配 `SY202609240008` |
| 写操作二次确认弹窗 | 出现并确认 |
| **ADM-S09 执行上架** | `POST /admin/sync/tasks/7/execute → 200 code=0` |
| **渠道绑定表出现该渠道** | `binding_id=4 channel_id=1004 status=ENABLED` |
| **渠道状态回读一致** | `last_synced_at=2026-09-24T14:31:37Z readback=有` |
| 任务终态非失败 | `status=SYNCED readback_equal=true operations=2 条` |
| 无异常业务码 | 27 次调用全部 `code=0` |
| 控制台 0 报错 | （忽略 1 条 429 资源加载噪声） |
| 同步页样式未退化 | 主按钮 `rgb(64,158,255)`、页底色未变 |

**接口调用序列（28 次，除首条频控外全部 code=0）**：其中
`POST /admin/sync/tasks`、`POST /admin/sync/tasks/7/execute`、`GET /admin/sync/tasks/7`（详情抽屉）、
`GET /admin/channel-bindings`（回读）全部由**浏览器页面真实发出**——不是脚本直连接口。

### 2. 管理端页面门禁 `admin-acceptance.mjs` —— 15/15 PASS

10 个页面逐页判据；本轮同步收紧了 4 处：
`/sync` 改判为「必须能点开对话框并渲染字段」（原为「只读三卡 + 未接线说明」——旧判据会放过现在的缺陷）、
`/usage` 补「聚合刷新入口」断言、`/detection` 删除已过期断言（`D-ADM-5` 已于 09-23 由 ADM-DET01 关闭）、
新增 `/compilation` 页判据（此前已实现却无业务判据，被误报「状态不明」）。

### 3. 构建与单测

- `npm run build` ✓（`vue-tsc --noEmit` 通过）
- `npm test` ✓ **54 passed**

### 4. 后端（T15，同一闭环的另一半）

- `SyncPublishContractTest` **7/7** 绿（`green-SyncPublish.txt`）
- 全量回归 **252 例 / 0 Failure / 0 Error**（BUILD SUCCESS）
- 后端直连闭环 `tools/biz-closure-e2e.py` **27/27**（`biz-closure-run3.json`）

---

## 三、闭环逐段状态（三端）

| 环节 | 触发方 | 真实结果 |
|---|---|---|
| 供应商进件 / 档案 / 凭证 | 供应商端 | ✅ 通过 |
| 检测 | 供应商端 + 管理端放行 | ⚠️ 本地靠 DET-06 人工放行（真实厂商接口下才自然 PASS） |
| 报价 / 审核 | 供应商端 + 管理端 | ✅ 通过 |
| 合同签署 / 打款确认 | 管理端 | ✅ 通过（打款止于 CONFIRMED） |
| 编译验证 | 管理端 | ✅ 通过（含本轮发现的 `E-2001` 缺陷修复） |
| **登记 new-api 端点** | **管理端（本轮接线）** | ✅ `POST /admin/newapi-endpoints` |
| **发起上架同步** | **管理端（本轮接线）** | ✅ `task_no=SY202609240008` |
| **执行上架 → new-api 建渠道** | **管理端（本轮接线）** | ✅ `channel_id=1004`，上游回读一致 |
| 用量回流 | 管理端（本轮接线 ADM-U02） | ✅ 可触发；数据源见缺口 ② |

---

## 四、提交与推送

| 提交 | 内容 |
|---|---|
| `005358e` | 管理端接线（6 文件）+ 验收脚本 |
| `3abb877` | 补登 ADM-S07/S08/S09 的 4 个 json-schema 产物（T15 漏提交） |
| `0aeded4` | T16 台账 + R355 误登记修正 |

已推送到远端 `main`：`git ls-remote` 回读 = `0aeded4f00d3554e8b61bbf7c512ef8d7895b393`，与本地 HEAD **严格一致**。

---

## 五、已知缺口（4 项，均需产品/环境侧输入）

1. **结算单生成口径未定（D-SETTLE-01）** ——
   出账周期 / `platform_fee` 计费基数 / 金额计算基数三件事在 PRD 全目录**零定义**；
   自造算法会直接影响真实对账金额，故**不猜**，`ADM-PAY03` 因此恒空。**需产品拍板**。
2. **用量真实源未接入（D-USAGE-01）** ——
   当前写入源是本地日志文件适配器，非 new-api Log 表 / `SumUsedQuota`；且缺 T+5min 定时聚合任务。
3. **真实 new-api 未接入** —— 本轮与 T15 均使用本地一体桩 `tools/newapi-stub.py`（明确标注非交付路径）。
4. **检测自然通过依赖真实厂商接口** —— 本地走 DET-06 人工放行。

## 六、台账修正（防后续会话照错行执行）

R355 第 27 类只读取证的 A2c 表登记「管理端 9 条零接线」，经复核其中
`ADM-AUTH01`（`views/login/index.vue:94`）与 `ADM-Q03`（`views/reviews/index.vue:203`）**已有真实调用点**，
该两行已过期 ⇒ A2c 实为 **7 条**。已在台账说明。

---

## 七、复跑方式

```bash
cd /e/workspaces/hioas/hioas-aap-001

# 后端（8084）
bash tools/run-dev-server.sh
# 本地上游桩（9911）—— 用法见脚本头部
python tools/newapi-stub.py --port 9911 --api-key <本地桩key> --state <state.json>

# 管理端（5174）
cd aap-admin && npm run dev
# 页面门禁 + UI 上架闭环
node tools/admin-acceptance.mjs http://127.0.0.1:5174 evidence/admin-<date> 13800000221
node tools/publish-e2e.mjs     http://127.0.0.1:5174 evidence/publish-e2e   13800000221
```

> 注意：同一手机号 60 秒内重复取码会命中考频控（`E-1903`），两个脚本均会等待后重试。
