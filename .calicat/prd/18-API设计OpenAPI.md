# API设计OpenAPI

# API 设计（OpenAPI 3.1）

> 完整规范见 `05-架构/03-API设计-openapi.yaml`（153KB，本卡片为接口结构摘要）。

## 通用约定

* 路径前缀 `/api/v1`；鉴权 `Authorization: Bearer <JWT>`（声明 sub/role/subjectType/providerId/exp/jti）。
* 角色：供应商端 role=PROVIDER；管理端 role∈{OPERATION\_BIZ 运营商务, TECH\_OPS 技术运营, SUPER\_ADMIN 超管}，`/admin/**` 仅管理端。
* 错误结构统一 ApiError（code+message+traceId+details\[]）；分页 page/pageSize（默认 20 上限 200）深分页改 cursor；非幂等写支持 Idempotency-Key（24h）；乐观锁 If-Match；时间 RFC3339 UTC；金额单价 USD/1M tokens；脱敏 apiKeyMask `sk-****abcd` 手机号 `138****8888`。
* new-api 集成边界：不直接透传 new-api 路径给前端，`/admin/sync/**` 是唯一对外同步入口。

## 接口清单（按 Tag）

**Auth**：POST /auth/sms/send、/auth/sms/login、/auth/wechat/login、/auth/refresh、/auth/logout、GET /auth/me。
**Provider**：/provider/profile、/provider/qualifications、/provider/qualifications/{id}；/admin/providers、/admin/providers/{id}/suspend、/resume。
**Credential**：/credentials、/credentials/{id}、/{id}/precheck、/{id}/precheck/latest、/{id}/reveal（超管二次验证）。
**Detection**：/detection-jobs、/{jobId}、/{jobId}/cancel、/{jobId}/results、/{jobId}/results/{probeCode}、/{jobId}/release（人工放行）。
**Report**：/reports、/{reportId}、/{reportId}/html、/{reportId}/export。
**Quote**：/quotes、/{quoteId}、/{quoteId}/items、/items/{itemId}、/{quoteId}/submit、/withdraw、/versions、/compile-preview；/admin/quotes/{id}/compile、/compilations、/admin/quotes/compare。
**Compilation**：/admin/compilations/{id}、/{id}/verify、/{id}/confirm。
**Review**：/admin/reviews、/{id}/claim、/approve、/reject、/records。
**Contract**：/contracts、/{id}、/admin/contracts、/admin/contracts/{id}/issue、/contracts/{id}/file、/sign、/admin/contracts/{id}/confirm-sign。
**Payment**：/payments、/admin/payments、/admin/payments/{id}/confirm、/admin/settlements。
**Sync**：/admin/sync/tasks、/{taskId}、/{taskId}/retry、/admin/channel-bindings、/{bindingId}/status、/admin/sync/models/upstream。
**Usage**：/usage/hourly、/usage/summary、/admin/usage/hourly、/admin/usage/refresh。
**Config**：/admin/detection-configs、/{configId}、/{configId}/publish、/admin/report-templates、/{templateId}、/{templateId}/publish。
**Audit/Notification**：/admin/audit-logs、/notifications、/notifications/{id}/read。
