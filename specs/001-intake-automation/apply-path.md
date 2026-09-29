# APPLY 执行路径接入设计（T-M4-10 / T-M4-11 的落点）

> 状态：**接入坐标已全部实测查明；代码尚未编写**。本文是为了让下一批实现「照着做即可」，
> 不是「已完成」的记录。凡是未实测的，一律标「待实测」。

## 1. 现状（实测）

| 环节 | 位置 | 行为 |
|---|---|---|
| 端点 | `supply/AdminSupplyUnitController.java`:38–82 | ADM-SU01~04 已注册，契约 117 全绿 |
| 端点 | `supply/AdminConfigBatchController.java`:33–78 | ADM-CB01~05 已注册 |
| APPLY 分支 | `supply/ConfigBatchAdminService.java`:127 | `batchStatus = mode == DRY_RUN ? "SUCCEEDED" : "PENDING"` |
| APPLY 明细 | `supply/ConfigBatchAdminService.java`:158 | 明细置 `SKIPPED`（dry-run）/ `PENDING`（apply） |
| 自述边界 | `SupplyUnitAdminService.java`:42/159、`ConfigBatchAdminService.java`:42 | 「`APPLY` 只登记受理态；执行器待 T-M4-08~11」 |
| 批次负载 | `ConfigBatchAdminService.java`:394 | `payload.put("executor", "PENDING")` |

**结论**：`APPLY` 目前**零上游写入**，`succeeded_count` 恒 0。闭环缺口 = 缺一个把 `PENDING`
明细变成真实上游调用、并把结果回写 `readback_equal`/`status` 的执行器。

## 2. 依赖坐标（全部实测，可直接引用）

### 2.1 上游调用客户端（复用，勿重写）
`sync/NewApiSyncClient.java`：
- `Probe get(String baseUrl, String apiKey, String path)`
- `Probe put(String baseUrl, String apiKey, String path, String jsonBody)`
- `Probe post(String baseUrl, String apiKey, String path, String jsonBody)`
- `Probe(boolean reachable, int httpStatus, String body, String errorCode, String error)`；`ok()` / `denied()`
- 内部已过 `OutboundUrlGuard`（SSRF 防护）—— **不要绕过它直接发 HTTP**。

### 2.2 new-api 同步账号（调用方身份）
现有建渠道调用形态（`sync/SyncPublishService.java`:204）：
`newApiSyncClient.post(endpoint.baseUrl(), endpoint.apiKey(), "/api/channel/", body)`
即：**new-api 地址 + 同步账号 key** 来自 `aap_newapi_endpoint`（非供应商凭据）。

### 2.3 供应商凭据（渠道的 key / base_url）
表 `aap_credential`（`V1__baseline.sql`:207）关键列：
`id, provider_id, base_url, api_key_cipher, api_key_mask, detection_status, primary_flag, deleted`

取 active 凭据（`SyncPublishService.java`:378–388 的既有口径，**必须沿用**）：
```sql
select id, base_url, api_key_cipher, detection_status from aap_credential
 where provider_id = ? and deleted = false order by id desc
```
逐个候选判断 `detection_status == "PASS"`，取第一个；**没有 PASS 凭据 → 抛 `E-1601`**
（理由：未检测通过的凭证不允许上生产路由）。

解密：`CryptoService.decrypt(String cipherText)`（`common/CryptoService.java`:72）。
脱敏展示：`CryptoService.maskApiKey(String)`（:122）—— **写日志/落 `request_summary` 前必须过它**（宪法 C-03）。

### 2.4 建渠道请求体（既有字段，`SyncPublishService.java`:197–202）
```java
channel.put("name", 渠道名);         // 由 ChannelNameGenerator 生成（R-54，≤64 字符）
channel.put("key", credential.apiKey());   // 解密后的供应商 key
channel.put("base_url", credential.baseUrl());
channel.put("models", String.join(",", models));  // PER_MODEL 下为单模型
channel.put("group", "default");
channel.put("tag", "aap-provider-" + providerId);
channel.put("status", 1);
```
序列化用 `common/JsonCodec.toJson(Map)`。

## 3. 执行流程（建议实现）

`ConfigApplyExecutor.execute(long batchId, int ratePerSec) -> List<ItemOutcome>`

1. 取该批次 `status = 'PENDING'` 的明细（含 `supply_unit_id` → 供应商 / 模型 / 目标渠道名）。
2. 对每条明细（**逐条 try/catch，互不影响** —— R-59）：
   1. 取 new-api 同步账号 + 该供应商 active 凭据（无 → 该项 `FAILED`，错误码 `E-1601`）。
   2. `POST /api/channel/` 建渠道。
   3. 失败分类：`denied()` → `E-1505` 权限问题（**该批应整体停并转人工**，不退避重试：重试也不会变好）；
      其余失败 → 按 `ConfigApplyRateLimiter.backoffSeconds(attempt)` 退避，`retryable(attempt)` 为假则 `FAILED`。
   4. 成功后 `GET /api/channel/{id}` **回读**，用 `ReadbackComparator.compare(期望, 回读)` 判定：
      一致 → `SUCCEEDED` + `readback_equal = true`；
      不一致 → **`MISMATCH`** + `readback_equal = false` + `readback_diff` 落库（R-58：不得静默成功）。
   5. 写库：`status / readback_equal / readback_diff / attempt_count / last_error / updated_at`。
   6. 限速：两次上游调用之间 `Thread.sleep(ConfigApplyRateLimiter.intervalMillis(ratePerSec))`。
3. 收尾：重算 `succeeded_count / failed_count / mismatch_count / status`；
   `diff_payload.executor` 由 `PENDING` 改为终态（当前 :394 写的是字面量 `"PENDING"`）。
4. 审计：每次执行落 `AuditService.record(AuditAction.SYNC_EXECUTE, "config_batch", batchId, 摘要)`。

## 4. 事务边界（关键设计）

- **批次级不得用一个长事务**：上游调用是网络 I/O，把它包进事务会长时间持有连接并放大锁冲突。
- 建议：`execute` 本身 `@Transactional(propagation = NOT_SUPPORTED)`；**每条明细的落库用一个独立短事务**
  （`TransactionTemplate` 或抽一个 `@Transactional(REQUIRES_NEW)` 的记录方法），
  这样「第 3 项失败」不会回滚「第 1、2 项已成功的结果」—— 这正是单模型隔离要的效果。
- 重试入口 `ConfigBatchAdminService`:219–235（`FAILED`/`MISMATCH` → `PENDING`，`attempt_count + 1`）已存在，
  执行器只需能被再次调用。

## 5. 失败矩阵

| 情形 | 明细终态 | 批次 | 是否退避重试 |
|---|---|---|---|
| 建渠道 HTTP 2xx + 回读一致 | `SUCCEEDED` | 继续 | — |
| 建渠道 HTTP 2xx + 回读不一致 | `MISMATCH` | `mismatch_count + 1`，批次可完成但**必须可见** | 否（需人工判断，重试可能掩盖问题） |
| 建渠道被拒（权限 `denied`） | `FAILED` | **整批转人工** | 否（重试不变好） |
| 建渠道 5xx / 网络失败 | `FAILED` | 继续其它项 | 是（30s/2m/10min，3 次后转人工） |
| 无 PASS 凭据 | `FAILED` | 继续其它项 | 否 |

## 6. 待实测（不得写成已定）

- **T-6**：桩 `tools/newapi-stub.py`（9911）对 `POST /api/channel/` 的响应体是否含新建渠道 `id`；
  若不含，回读需改用 `GET /api/channel/?name=<渠道名>` 定位（当前桩不支持按名查询，见 T-1 记录）。
- **T-7**：真实 new-api 的 `PUT /api/channel/` 是「全量覆盖」还是「字段合并」——直接影响重配置（UPDATE）
  是否需要先 GET 再合并写回，避免抹掉网关侧其它字段。
- **T-8**：`aap_newapi_endpoint` 的列名与 active 选取口径需按实现当日实测确认（本文只确认了调用形态，
  未确认该表列名）。

## 7. 变更登记

| 日期 | 变更 | 依据 |
|---|---|---|
| 2026-09-29 | 初稿：接入坐标实测查明（凭据口径、payload 字段、接入点行号、失败矩阵） | `ConfigBatchAdminService` / `SyncPublishService` / `NewApiSyncClient` / `V1__baseline.sql` 源码 |
