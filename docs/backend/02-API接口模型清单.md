# AAP 服务端 API 接口模型清单（开发前冻结）

> **本文件是开发前置产物**：所有接口在本文件逐条列出并冻结 ID（`AUTH-01`…），
> 实现、测试、验收一律按 ID 对应，任何新增/变更接口先改本文件再改代码。
>
> 依据：`.calicat/prd/18-API设计OpenAPI.md`（路径清单）+ `aap-client/src/api/*.ts`（客户端真实调用）
> + `docs/api/接口字段级schema.md`（供应商端字段级补充）+ `17-零歧义执行规格spec.md`（错误码/状态机）。
> 模型定义：请求/响应体的 JSON Schema 见 `json-schema/**`，OpenAPI 见 `openapi.yaml`。

**版本** v1.0 · 2026-09-17 · 共 **99 条**端点（供应商端 49 · 管理端 50，与 `openapi.yaml` 生成器逐条同源）。

**标注规则**

| 标记 | 含义 |
|---|---|
| `真源` | 方法/参数/字段有 PRD 或客户端代码直接依据 |
| `推断` | 18-API 只列路径未列方法/参数 → 按 REST 语义推断（D-CALICAT-01），待完整 spec 回归 |
| `约定` | 22 份 PRD 零命中，但 `aap-client` 已消费 → 后端必须提供（D-PRD-01） |
| 状态列 | `待实现` / `Txx`（任务号） / `已实现` |

---

## 0. 通用约定（所有接口）

| 项 | 约定 |
|---|---|
| 前缀 | `/api/v1` |
| 鉴权 | `Authorization: Bearer <jwt>`；JWT claims：`sub`(账号 id) `role` `subjectType`(PROVIDER/ADMIN) `providerId` `exp` `jti` |
| 响应包体 | `{"code":"0|E-xxxx","message":"...","data":{...},"traceId":"..."}` |
| 分页 | 请求 `page`（默认 1）/ `pageSize`（默认 20，上限 200）；响应 `data:{items:[],page,pageSize,total}`（**字段名以客户端为准**：`aap-client/src/utils/credentials-model.ts` 等读 `raw.items`；`list` 仅是 messages 适配器的兜底。原文档 `docs/api/接口字段级schema.md` 写 `list`，与本清单冲突 → 见偏差 D-API-01） |
| 幂等 | 非幂等写支持 `Idempotency-Key`（24h，命中返回首次响应体，C11） |
| 乐观锁 | 需并发保护的写支持 `If-Match: <version 或 updated_at>`；不匹配 → 409 + `E-1601` |
| 时间 | RFC3339 **UTC**；小时桶为整点；`DATE` 字段 `yyyy-MM-dd` |
| 金额 | 真实单价 `USD / 1M tokens`，`numeric(18,6)`；总额 USD |
| 脱敏 | `api_key_mask`=`sk-****abcd`（R-05）；手机号 `138****8888`（R-48）；**后端永不回明文** |
| 缺字段 | 一律 `null` 或省略，前端显示占位；**禁止 0 冒充"没有数据"**（例外 `cache_parse_status=NO_CACHE_FIELD` 明确记 0） |
| 排序 | 列表默认 `created_at desc, id desc` |
| traceId | 响应头 `X-Trace-Id` 与包体 `traceId` 一致，同时写入日志与审计 |

---

## 1. 供应商端接口（`aap-client` 消费）

### 1.1 Auth（账号接入）

| ID | 方法 | 路径 | 鉴权 | 请求 | 响应 | 错误码 | 幂等/并发 | 依据 | 状态 |
|---|---|---|---|---|---|---|---|---|---|
| AUTH-01 | POST | `/auth/sms/send` | 免 | body `{phone, captcha}` | `{ttl:300}` | E-1001 E-1903 | 60s 频控（R-02） | 真源 | T03 |
| AUTH-02 | POST | `/auth/sms/login` | 免 | body `{phone, smsCode}` | `LoginResult{token,role,providerId,status,refreshToken}` | E-1001 E-1101 | 5 次错锁 15 分钟 | 真源 | T03 |
| AUTH-03 | POST | `/auth/wechat/login` | 免 | body `{code}` | `LoginResult` | E-1001 | | 真源 | T03 |
| AUTH-04 | POST | `/auth/refresh` | 免 | body `{refreshToken}` | `LoginResult` | E-1902 | | 推断 | T03 |
| AUTH-05 | POST | `/auth/logout` | ✅ | — | `null` | | | 真源 | T03 |
| AUTH-06 | GET | `/auth/me` | ✅ | — | `MeResult{phone,masked…,role,providerId,providerCode,status,wechat_bound,sms_2fa,wechat_subscribed}` | E-1902 | | 真源 + 约定 | T03 |

> AUTH-06 的 `wechat_bound / sms_2fa / wechat_subscribed` 供「我的设置」页消费（序号 23，`src/utils/settings-model.ts`）→ 标注 `约定`。

### 1.2 Provider（供应商主体与资质）

| ID | 方法 | 路径 | 鉴权 | 请求 | 响应 | 错误码 | 幂等/并发 | 依据 | 状态 |
|---|---|---|---|---|---|---|---|---|---|
| PROV-01 | GET | `/provider/profile` | ✅ | — | `ProviderProfile` | E-1101 | | 真源 | T04 |
| PROV-02 | PUT | `/provider/profile` | ✅ | body：`company_name` `uscc` `contact_name` `contact_phone` `contact_email` `contact_title` `province` `city` `address` `website` `company_intro` `recheck_interval_days` `short_name` `industry_category` | `ProviderProfile` | E-1001 E-1104 | `Idempotency-Key` + `If-Match` | 真源 + 约定 | T04 |
| PROV-03 | GET | `/provider/qualifications` | ✅ | q：`page` `pageSize` | `{items:[ProviderQualification],page,pageSize,total}` | | | 真源 | T04 |
| PROV-04 | POST | `/provider/qualifications` | ✅ | body：`category` `file_name` `file_size` `content_type` `file_id?` | `Qualification` | E-1001 | `Idempotency-Key` | 真源 | T04 |
| PROV-05 | DELETE | `/provider/qualifications/{id}` | ✅ | — | `null` | E-1901 E-2001 | | 真源 | T04 |

> **PROV-04 双语义**：`aap-client` 的「接入凭证/准入表单」（序号 4-v1）用同一端点提交企业信息 + 资质登记；
> 服务端按「资质登记 + 触发首次检测」处理（09-PRD §5 的服务端副作用），**前端不重复建检测任务**。

### 1.3 Credential（测试凭证）

| ID | 方法 | 路径 | 鉴权 | 请求 | 响应 | 错误码 | 幂等/并发 | 依据 | 状态 |
|---|---|---|---|---|---|---|---|---|---|
| CRED-01 | GET | `/credentials` | ✅ | q：`page` `pageSize` `status?` | `{items:[CredentialRow],page,pageSize,total}` | | | 真源 | T05 |
| CRED-02 | POST | `/credentials` | ✅ | body：`alias` `base_url` `api_key` `primary_flag` `declared_vendor` `declared_rpm` `declared_tpm` `declared_context_window` `model_list[]` | `CredentialDetail` | E-1001 E-1104 E-1201 | `Idempotency-Key` | 推断 | T05 |
| CRED-03 | GET | `/credentials/{id}` | ✅ | — | `CredentialDetail` | E-1901 | | 真源 | T05 |
| CRED-04 | PUT | `/credentials/{id}` | ✅ | body：同 CRED-02 的可写子集（`api_key?` 轮换） | `CredentialDetail` | E-1001 E-1104 | `If-Match` | 真源 | T05 |
| CRED-05 | POST | `/credentials/{id}/precheck` | ✅ | — | `{job_id,precheck_status,status}` | E-1101 E-1201 E-1301 | `Idempotency-Key`（C2 互斥） | 真源 | T05 |
| CRED-06 | GET | `/credentials/{id}/precheck/latest` | ✅ | — | `Precheck` | E-1101 | | 推断 | T05 |
| CRED-07 | POST | `/credentials/{id}/reveal` | ✅ 超管 | body `{smsCode}` | `{api_key}`（仅此一次明文） | E-1901 E-1902 | 二次验证 + 审计（AC-30） | 真源 | T05 |

> CRED-01 的 `detection_status`（`PENDING/RUNNING/PASS/FAIL`）与 `latest_report_id` 是**服务端派生列**，
> 供列表页状态 chips 与「报告」入口消费（`src/utils/credentials-model.ts`）。

### 1.4 Detection（检测任务）

| ID | 方法 | 路径 | 鉴权 | 请求 | 响应 | 错误码 | 幂等/并发 | 依据 | 状态 |
|---|---|---|---|---|---|---|---|---|---|
| DET-01 | POST | `/detection-jobs` | ✅ | body `{credential_id, trigger_type?}` | `{job_id,job_no,status}` | E-1301 E-1302 E-1303 | `Idempotency-Key`；C2 互斥；日配额 5 次（R-09） | 真源 | T06 |
| DET-02 | GET | `/detection-jobs/{jobId}` | ✅ | — | `DetectionJob`（含 `progress{}`） | E-1304 E-1901 | | 真源 | T06 |
| DET-03 | GET | `/detection-jobs/{jobId}/results` | ✅ | — | `{job_id,total,items:[DetectionResult]}` | E-1304 | | 真源 | T06 |
| DET-04 | GET | `/detection-jobs/{jobId}/results/{probeCode}` | ✅ | — | `DetectionResult` | E-1304 | | 推断 | T06 |
| DET-05 | POST | `/detection-jobs/{jobId}/cancel` | ✅ | — | `DetectionJob` | E-1305 E-1601 | | 推断 | T06 |
| DET-06 | POST | `/detection-jobs/{jobId}/release` | ✅ 管理端 | body `{override_reason}` | `DetectionJob` | E-1601 | R-47a 理由必填；审计 | 真源 | T06 |

### 1.5 Report（检测报告）

| ID | 方法 | 路径 | 鉴权 | 请求 | 响应 | 错误码 | 幂等/并发 | 依据 | 状态 |
|---|---|---|---|---|---|---|---|---|---|
| RPT-01 | GET | `/reports` | ✅ | q：`page` `pageSize` `result?` | `{items:[ReportRow],page,pageSize,total}` | | | 真源 | T07 |
| RPT-02 | GET | `/reports/{reportId}` | ✅ | — | `Report`（详情/未通过页共用） | E-1401 | | 真源 | T07 |
| RPT-03 | GET | `/reports/{reportId}/html` | ✅ | — | `text/html` | E-1401 | | 推断 | T07 |
| RPT-04 | GET | `/reports/{reportId}/export` | ✅ | — | `{url,file_name,expire_at}` | E-1401 | | 真源 | T07 |

> RPT-02 需同时满足「多维度专业版」（序号 6：`sections/issues/evidence/key_metrics`）
> 与「未通过报告」（序号 7：`dims/detail/veto_note`）两套消费口径 → 响应为**超集**，两种页面各取所需。

### 1.6 Quote（报价单与定价）

| ID | 方法 | 路径 | 鉴权 | 请求 | 响应 | 错误码 | 幂等/并发 | 依据 | 状态 |
|---|---|---|---|---|---|---|---|---|---|
| QT-01 | GET | `/quotes` | ✅ | q：`page` `pageSize` `status`(逗号分隔多值) | `{items:[QuoteRow],page,pageSize,total}` | | | 真源 | T08 |
| QT-02 | POST | `/quotes` | ✅ | body：`name` `provider_id` `credential_id` `remark` `valid_from` `valid_to` `currency` | `Quote{build:quote_id,quote_no,status,items[]}` | E-1602 E-1001 | `Idempotency-Key` | 真源 | T08 |
| QT-03 | GET | `/quotes/{quoteId}` | ✅ | — | `QuoteDetail`（报价单 + `items[]` + 可含规则） | E-1406 | | 真源 | T08 |
| QT-04 | DELETE | `/quotes/{quoteId}` | ✅ | — | `null` | E-1601 | | 真源（PRD 口径为「作废 VOID」，已记台账冲突） | T08 |
| QT-05 | POST | `/quotes/{quoteId}/items` | ✅ | body `{items:[{model_name,model_alias?}]}` | `{items:[QuoteItem]}` | E-1001 E-1401 | `Idempotency-Key` | 真源 | T08 |
| QT-06 | GET | `/quotes/{quoteId}/items` | ✅ | — | `{items:[QuoteItem],total}` | E-1406 | | 真源 | T08 |
| QT-07 | GET | `/quotes/items/{itemId}` | ✅ | — | `QuoteItem`（含 `time_rule`/`tier_rule`/`request_rules`） | E-1406 | | 真源 | T08 |
| QT-08 | PUT | `/quotes/items/{itemId}` | ✅ | body：八大单价 + `price_time_rule?` + `price_tier_rule?` + `request_rules?` + `note` | `QuoteItem`（含 `warnings[]`） | E-1001 E-1401 E-1402 E-1403 E-1404 E-1104(If-Match 失配) | `If-Match` | 真源（E-1104 为推断） | T08 |
| QT-09 | POST | `/quotes/{quoteId}/submit` | ✅ | —（无请求体） | `QuoteDetail` | E-1001 E-1401 E-1402 E-1601 E-1602 | `Idempotency-Key` | 真源 | T08 |
| QT-10 | POST | `/quotes/{quoteId}/withdraw` | ✅ | — | `QuoteDetail` | E-1601 | | 真源 | T08 |
| QT-11 | GET | `/quotes/{quoteId}/versions` | ✅ | `page/pageSize` | `{items:[QuoteVersion],total}` | E-1401 | | 推断 | T08 |
| QT-12 | POST | `/quotes/{quoteId}/compile-preview` | ✅ | — | `{compiled:[ModelExpression],gate_status,verify_report}` | E-1401 E-1402 E-1405 | `Idempotency-Key` | 真源 | T09 |

### 1.7 Contract / Payment / Notification（合同 · 打款 · 站内信）

| ID | 方法 | 路径 | 鉴权 | 请求 | 响应 | 错误码 | 幂等/并发 | 依据 | 状态 |
|---|---|---|---|---|---|---|---|---|---|
| CON-01 | GET | `/contracts` | ✅ | q：`page` `pageSize` `status?` | `{items:[Contract],page,pageSize,total}` | | | 真源 | T11 |
| CON-02 | GET | `/contracts/{id}` | ✅ | — | `Contract`（含 `terms[]` `records[]`） | E-1701 | | 真源 | T11 |
| CON-03 | GET | `/contracts/{id}/file` | ✅ | — | `{url,file_name}` | E-1701 | | 真源 | T11 |
| CON-04 | POST | `/contracts/{id}/sign` | ✅ | body `{sign_method?,smsCode?}` | `Contract` | E-1701 E-1601 | `Idempotency-Key` | 真源（路径为推断：卡片 `/sign` 挂到合同下） | T11 |
| PAY-01 | GET | `/payments` | ✅ | q：`page` `pageSize` | `{items:[Payment],page,pageSize,total,available_balance?,pending_settlement?,total_settled?}` | | | 真源 + 约定（钱包三项无 PRD 依据） | T11 |
| NTF-01 | GET | `/notifications` | ✅ | q：`page` `pageSize` `unread?` `category?` | `{items:[Notification],page,pageSize,total,unread_count}` | | | 真源 + 推断（参数名） | T13 |
| NTF-02 | POST | `/notifications/{id}/read` | ✅ | — | `{id,read_at}` | E-1901 | | 真源 | T13 |

### 1.8 Usage（用量统计）

| ID | 方法 | 路径 | 鉴权 | 请求 | 响应 | 错误码 | 幂等/并发 | 依据 | 状态 |
|---|---|---|---|---|---|---|---|---|---|
| USE-01 | GET | `/usage/summary` | ✅ | q：`startHour?` `endHour?` `month?` | `UsageSummary`（见 `docs/api/接口字段级schema.md` §1） | E-1801 | | 真源 | T12 |
| USE-02 | GET | `/usage/hourly` | ✅ | q：`from` `to` `model?` `group?` `page` `pageSize` | `{items:[UsageHourlyBucket],page,pageSize,total}` | E-1801 | | 真源 | T12 |

> `month` 参数（序号 22 用量概览页）在 18-API 未列 → `推断`。
> `/usage/summary` 需同时满足工作台（环形图/模型 Top3）与用量页（逐日趋势/成本构成）→ 响应为超集。

---

## 2. 管理端接口（`/admin/**`，仅管理端角色）

### 2.1 供应商与凭证

| ID | 方法 | 路径 | 角色 | 请求/响应 | 错误码 | 状态 |
|---|---|---|---|---|---|---|
| ADM-P01 | GET | `/admin/providers` | BIZ_OPERATOR TECH_OPS SUPER_ADMIN | q：`page` `pageSize` `status?` `keyword?` → 分页 `Provider` | | T14 |
| ADM-P02 | POST | `/admin/providers/{id}/suspend` | 同上 | body `{suspend_reason}` → `Provider` | E-1601 | T14 |
| ADM-P03 | POST | `/admin/providers/{id}/resume` | 同上 | → `Provider` | E-1601 | T14 |
| ADM-C01 | GET | `/admin/credentials/{id}` | SUPER_ADMIN | → `CredentialDetail`（含 `api_key_mask`） | E-1901 | T14 |
| ADM-C02 | POST | `/admin/credentials/{id}/reveal` | SUPER_ADMIN | body `{smsCode}` → `{api_key}` + 审计 | E-1901 E-1902 | T14 |

### 2.2 报价 / 编译 / 审核

| ID | 方法 | 路径 | 角色 | 请求/响应 | 错误码 | 状态 |
|---|---|---|---|---|---|---|
| ADM-Q01 | POST | `/admin/quotes/{id}/compile` | TECH_OPS SUPER_ADMIN | → `CompilationResult` | E-1401~E-1405 E-1601(未审核通过) | T09 |
| ADM-Q02 | GET | `/admin/quotes/compare` | BIZ_OPERATOR SUPER_ADMIN | q：`quoteIds`(逗号) → `{items:[QuoteCompare]}`（旧值/新值/涨跌幅 A8） | | T14 |
| ADM-Q03 | GET | `/admin/quotes/{id}/items` | BIZ_OPERATOR SUPER_ADMIN | → `QuoteViews.Items`（管理端**跨供应商只读**报价明细；报价审核页消费） | E-1406 | T14 |
| ADM-CP01 | GET | `/admin/compilations` | TECH_OPS | q：`page` `pageSize` `status?` → 分页 | | T09 |
| ADM-CP02 | GET | `/admin/compilations/{id}` | TECH_OPS | → `CompilationResult`（含 `compiled[]` `verify_report`） | E-1406 | T09 |
| ADM-CP03 | POST | `/admin/compilations/{id}/verify` | TECH_OPS | → `VerifyReport`（V1–V6） | E-1405 | T09 |
| ADM-CP04 | POST | `/admin/compilations/{id}/confirm` | TECH_OPS SUPER_ADMIN | → `CompilationResult`（`gate_status=CONFIRMED`，解锁写入） | E-1405 E-1407 | T09 |
| ADM-R01 | GET | `/admin/reviews` | BIZ_OPERATOR TECH_OPS | q：`page` `pageSize` `status?` → 分页 `ReviewTask` | | T10 |
| ADM-R02 | POST | `/admin/reviews/{id}/claim` | BIZ_OPERATOR | → `ReviewTask`（乐观锁 E1） | E-1601 | T10 |
| ADM-R03 | POST | `/admin/reviews/{id}/approve` | BIZ_OPERATOR | body `{comment?}` → `ReviewTask`（→ APPROVED，自动生成合同） | E-1601 | T10 |
| ADM-R04 | POST | `/admin/reviews/{id}/reject` | BIZ_OPERATOR | body `{reason_code,reason_text,item_id?}`（**必填**） | E-1001 E-1601 | T10 |
| ADM-R05 | GET | `/admin/reviews/records` | 同上 | q：`quoteId?` → `{items:[ReviewRecord]}` | | T10 |

> **为什么新增 ADM-Q03**：报价审核页原先调供应商端点 `GET /quotes/{id}/items`
> （`hasAnyRole('SUPPLIER','PROVIDER')`）→ 管理端令牌必然 **403** → **审核员看不到逐模型价格，只能盲审**
> （2026-09-23 运行态实测：详情页「该报价单暂无明细（或接口未返回）」+ 控制台 403）。不做归属校验
> （管理端本就跨供应商），但报价单必须存在且未删除，否则 `E-1406`。

### 2.3 合同 / 打款 / 结算

| ID | 方法 | 路径 | 角色 | 请求/响应 | 错误码 | 状态 |
|---|---|---|---|---|---|---|
| ADM-CT01 | GET | `/admin/contracts` | BIZ_OPERATOR | q：`page` `pageSize` `status?` → 分页 | | T11 |
| ADM-CT02 | POST | `/admin/contracts/{id}/issue` | BIZ_OPERATOR | body `{file_id,valid_from,valid_to,platform_fee_rate,...}` → `Contract`（CREATED→PENDING_SIGN） | E-1001 E-1601 | T11 |
| ADM-CT03 | POST | `/admin/contracts/{id}/confirm-sign` | BIZ_OPERATOR | → `Contract`（SUPPLIER_SIGNED→SIGNED） | E-1601 | T11 |
| ADM-PAY01 | GET | `/admin/payments` | BIZ_OPERATOR | q：分页 → 分页 `Payment` | | T11 |
| ADM-PAY02 | POST | `/admin/payments/{id}/confirm` | BIZ_OPERATOR SUPER_ADMIN | → `Payment`（PAYMENT_RECORDED→CONFIRMED） | E-1601 E-1701 | T11 |
| ADM-PAY03 | GET | `/admin/settlements` | BIZ_OPERATOR | q：分页 → 分页 `SettlementStatement` | | T11 |
| ADM-PAY04 | POST | `/admin/payments` | BIZ_OPERATOR SUPER_ADMIN | body `{contract_id,amount,currency?,voucher_file_id,paid_at?,remark?}` → `Payment`（**记录打款**：UNSETTLED→PAYMENT_RECORDED；C4 金额>0 且币种一致、C5 凭证必填；**不产生资金流水** R-42） | E-1001 E-1406 E-1601 | T11 |
| ADM-PAY05 | POST | `/admin/payments/{id}/void` | BIZ_OPERATOR SUPER_ADMIN | body `{reason}` → `Payment`（PAYMENT_RECORDED/CONFIRMED→**VOID**；必填理由，作废后可重录） | E-1001 E-1406 E-1601 | T11 |

### 2.4 同步 / 用量 / 配置 / 审计

| ID | 方法 | 路径 | 角色 | 请求/响应 | 错误码 | 状态 |
|---|---|---|---|---|---|---|
| ADM-S01 | GET | `/admin/sync/tasks` | TECH_OPS | q：`page` `pageSize` `status?` `bindingId?` → 分页 | | T14 |
| ADM-S02 | GET | `/admin/sync/tasks/{taskId}` | TECH_OPS | → `SyncTask`（含 operations） | E-1501 | T14 |
| ADM-S03 | POST | `/admin/sync/tasks/{taskId}/retry` | TECH_OPS | → `SyncTask`（≤5 次退避 30s/2m/8m/30m/2h） | E-1501 E-1505 | T14 |
| ADM-S04 | GET | `/admin/channel-bindings` | TECH_OPS | q：分页 → 分页 `ChannelBinding` | | T14 |
| ADM-S05 | POST | `/admin/channel-bindings/{bindingId}/status` | TECH_OPS | body `{target_status:ENABLED\|DISABLED}` → `ChannelBinding` | E-1505 | T14 |
| ADM-S06 | GET | `/admin/sync/models/upstream` | TECH_OPS | → `{models:[ModelInfo]}` | E-1505 | T14 |
| ADM-U01 | GET | `/admin/usage/hourly` | TECH_OPS BIZ_OPERATOR | q：`from` `to` `providerId?` `channelId?` `model?` `page` `pageSize` → 分页 | E-1801 | T12 |
| ADM-U02 | POST | `/admin/usage/refresh` | TECH_OPS | body `{from?,to?}` → `{batch_id,inserted,updated,cache_parse_status}`（UPSERT 幂等） | E-1801 | T12 |
| ADM-CFG01 | GET | `/admin/detection-configs` | TECH_OPS | q：分页 → 分页 `DetectionConfig` | | T14 |
| ADM-CFG02 | POST | `/admin/detection-configs` | TECH_OPS | body：`name` `pass_score` `veto_rule` `probes[]` → `DetectionConfig` | E-1001 | T14 |
| ADM-CFG03 | GET | `/admin/detection-configs/{configId}` | TECH_OPS | → `DetectionConfig` | E-1406 | T14 |
| ADM-CFG04 | PUT | `/admin/detection-configs/{configId}` | TECH_OPS | → `DetectionConfig`（DRAFT 可改） | E-1601 | T14 |
| ADM-CFG05 | POST | `/admin/detection-configs/{configId}/publish` | TECH_OPS | → `DetectionConfig`（旧版置 SUPERSEDED） | E-1601 | T14 |
| ADM-CFG06 | GET | `/admin/report-templates` | TECH_OPS | q：分页 → 分页 `ReportTemplate` | | T14 |
| ADM-CFG07 | POST | `/admin/report-templates` | TECH_OPS | body：`title` `logo_file_id` `section_order` `disclaimer` → `ReportTemplate` | E-1001 | T14 |
| ADM-CFG08 | GET | `/admin/report-templates/{templateId}` | TECH_OPS | → `ReportTemplate` | E-1406 | T14 |
| ADM-CFG09 | PUT | `/admin/report-templates/{templateId}` | TECH_OPS | → `ReportTemplate` | E-1601 | T14 |
| ADM-CFG10 | POST | `/admin/report-templates/{templateId}/publish` | TECH_OPS | → `ReportTemplate` | E-1601 | T14 |
| ADM-A01 | GET | `/admin/audit-logs` | TECH_OPS SUPER_ADMIN | q：`page` `pageSize` `actorType?` `action?` `traceId?` `from?` `to?` → 分页 `AuditLog` | E-1901 | T13 |
| ADM-DET01 | GET | `/admin/detection-jobs` | TECH_OPS SUPER_ADMIN | q：`page` `pageSize` `status?` `credentialId?` `providerId?` → 分页 `DetectionJob`（含 `provider_name`/`credential_alias`，管理端列表附加字段） | | 新增 |

> **为什么新增 ADM-DET01**：管理端此前**没有任何检测任务列表端点** —— 全仓管理端相关的只有
> `POST /detection-jobs/{jobId}/release`（按 id 放行），而 `DET-01…05` 全部限供应商本人（管理端 403）。
> 结果「检测中心」页 KPI 只能显「未知」、任务表为空、**人工放行需手输任务 ID**（运营无从得知 ID）
> → 人工放行实际不可用，而它是凭证拿到 `PASS`（进而报价）的唯一路径（2026-09-23 运行态实测）。
> 附加字段 `provider_name`/`credential_alias` 为**可选、向后兼容**（供应商侧接口保持 null）。

### 2.5 管理端账号接入（Auth）

| ID | 方法 | 路径 | 角色 | 请求/响应 | 错误码 | 状态 |
|---|---|---|---|---|---|---|
| ADM-AUTH01 | POST | `/admin/auth/sms/login` | 免（`SecurityConfig.PUBLIC_PATHS` 放行） | body `{phone, smsCode}` → `LoginResult{token,role,status}`（`subjectType=ADMIN`，role 取自 `aap_admin_user.role`） | E-1001 E-1901 E-1902 E-1903 | T14 |
| ADM-AUTH02 | GET | `/admin/admin-users` | SUPER_ADMIN | q：`page` `pageSize` `role?` `status?` `keyword?` → 分页 `AdminUser`（只出 `phone_masked`） | E-1901 | T14 |
| ADM-AUTH03 | POST | `/admin/admin-users` | SUPER_ADMIN | body `{username,display_name?,role,phone}` → `AdminUser`（手机号即登录名；`username`/`phone` 唯一；role 白名单 BIZ_OPERATOR/TECH_OPS/SUPER_ADMIN） | E-1001 | T14 |
| ADM-AUTH04 | POST | `/admin/admin-users/{id}/suspend` | SUPER_ADMIN | body `{reason}` → `AdminUser`（ACTIVE→SUSPENDED；不可停用自己、不可停用最后一个启用中超管） | E-1001 E-1406 E-1601 | T14 |
| ADM-AUTH05 | POST | `/admin/admin-users/{id}/resume` | SUPER_ADMIN | → `AdminUser`（SUSPENDED→ACTIVE） | E-1406 E-1601 | T14 |

> **为什么新增（ADM-AUTH02…05）**：`ADM-AUTH01` 打通管理端登录后，**建号仍只能靠 SQL**
> （13-管理端PRD 要求管理端账号可自助管理）。全部限 SUPER_ADMIN —— 建号/停用属提权操作。
> 本期无密码登录：`password_hash` 落不可用占位 `"!"`，登录一律走 `ADM-AUTH01` 短信码。
> `phone_hash` 列**无唯一索引**，故重复手机号由服务层拦截（否则短信登录将无法确定登录到哪个账号）。

> **为什么新增**：管理端此前**没有登录入口** —— `aap-admin` 登录页调的是供应商端点 `AUTH-02`，
> 而它固定签发 `subjectType=PROVIDER`，导致登录「成功」但 `/admin/**` 一律 403 `E-1901`
> （人工放行 `DET-06`、报价审核、配置发布在真实环境里全都调不动）。2026-09-23 运行态实测确证。
>
> 口径：验证码下发复用 `AUTH-01`（同一套 60s 频控 + 5 次错码锁 15 分钟）；**不自动注册** ——
> 手机号必须已存在于 `aap_admin_user` 且 `status=ACTIVE`，否则 `E-1902`。
> `AUTH-06 (/auth/me)` 对管理端主体返回管理端档案（此前会拿到 `E-1902`）。

---

## 3. 客户端 → 接口映射（可追溯）

| 客户端页面（序号） | 调用 | 接口 ID |
|---|---|---|
| 1 登录注册 | `authApi.sendSms/login/wechatLogin/me` | AUTH-01/02/03/06 |
| 2 工作台 | `usageApi.summary`、`providerApi.profile` | USE-01、PROV-01 |
| 3 凭证列表 | `credentialApi.list` | CRED-01 |
| 4 提交接入凭证 | `credentialApi.detail/save/precheck`、`accessApplicationApi.submit` | CRED-03/04/05、PROV-04 |
| 5 检测进行中 | `detectionApi.job/results` | DET-02/03 |
| 6 检测报告 | `reportApi.detail/exportFile` | RPT-02/04 |
| 7 未通过报告 | `reportApi.detail`、`detectionApi.create` | RPT-02、DET-01 |
| 8 报价单列表 | `quoteApi.list/remove` | QT-01/04 |
| 9 模型报价设置 | `credentialApi.list`、`providerApi.profile`、`quoteApi.create/setItems` | CRED-01、PROV-01、QT-02/05 |
| 10 供应商档案编辑 | `providerApi.profile/saveProfile` | PROV-01/02 |
| 10.1 供应商档案 | `providerApi.profile/qualifications` | PROV-01/03 |
| 11 模型定价详情 | `quoteApi.getItem/listItems/saveItem` | QT-06/07/08 |
| 12 报价预览提交 | `quoteApi.detail/listItems/submit` | QT-03/06/09 |
| 15 合同签署 | `contractApi.detail/file/sign` | CON-02/03/04 |
| 20 站内信列表 | `notificationApi.list/markRead` | NTF-01/02 |
| 21 我的 | `reportApi.list`、`quoteApi.list`、`contractApi.list`、`credentialApi.list`、`notificationApi.list`、`paymentApi.list`、`providerApi.profile` | RPT-01、QT-01、CON-01、CRED-01、NTF-01、PAY-01、PROV-01 |
| 22 用量概览 | `usageApi.overview` | USE-01 |
| 23 我的设置 | `authApi.me/logout` | AUTH-06/05 |

---

## 4. 错误码表（统一响应 `code`）

| 码 | HTTP | 场景 | 依据 |
|---|---|---|---|
| `0` | 200 | 成功 | |
| `E-1001` | 400 | 参数校验失败（手机号 `^1[3-9]\d{9}$`、验证码 6 位、uscc 18 位、金额<0…） | spec §9 |
| `E-1101` | 400 | 预检失败（连通性/鉴权） | |
| `E-1102` | 400 | 凭证状态不允许该操作 | |
| `E-1104` | 409 | 唯一性冲突（uscc 重复、api_key 指纹重复） | AC-09 |
| `E-1201` | 400 | SSRF 出站地址被拒 | AC-29 |
| `E-1301` | 409 | 检测互斥（同凭证已有活跃任务） | AC-13 |
| `E-1302` | 429 | 供应商日配额用尽（5 次） | R-09 |
| `E-1303` | 400 | 凭证不可检测（未预检通过/已失效） | |
| `E-1304` | 404 | 检测任务不存在/无权 | |
| `E-1305` | 409 | 任务不可取消（已终态） | |
| `E-1401` | 400 | 时段重叠 / 报价单不存在 | AC-24 |
| `E-1402` | 400 | 阶梯空洞或重叠 | AC-25 |
| `E-1403` | 400 | 倍率非法（≤0/NaN） | |
| `E-1404` | 400 | 阶梯首档 min≠0 或末档 max≠null | |
| `E-1405` | 400 | 模拟校验失败（定位字段） | AC-27 |
| `E-1406` | 404 | 编译产物/配置/模板不存在 | |
| `E-1407` | 409 | 未确认禁止写入（红线） | AC-28/33 |
| `E-1501` | 502 | 同步失败（new-api 不可达/回读不一致） | |
| `E-1505` | 403 | 权限不足（同步接口） | AC-50 |
| `E-1601` | 409 | 状态非法流转 | spec §4 |
| `E-1602` | 400 | 未通过检测不可报价 | AC-22 |
| `E-1701` | 409 | 合同未签署禁打款/合同状态非法 | AC-40 |
| `E-1801` | 503 | 用量聚合失败（降级返回最近可用窗口，**不返回 0 冒充**） | docs/api §4 |
| `E-1901` | 403 | 权限不足 | |
| `E-1902` | 401 | 未认证 / token 过期 | |
| `E-1903` | 429 | 限流（短信 60s 频控等） | |
| `E-2001` | 500 | 内部错误 | |

## 5. 全局枚举字典

| 枚举 | 取值 | 出处 |
|---|---|---|
| ProviderStatus | `PENDING_CREDENTIAL` `DETECTING` `DETECT_FAILED` `DETECT_PASSED` `QUOTING` `QUOTE_SUBMITTED` `CONTRACT_PENDING` `SIGNED` `PAID` `PUBLISHED` `SUSPENDED` `TERMINATED` | 17-spec §4 |
| DetectionJobStatus | `QUEUED` `RUNNING` `PARTIAL_DONE` `COMPLETED` `REPORT_GENERATED` `FAILED` | 17-spec §4 |
| ProbeStatus | `SUCCESS` `FAILED` `SKIPPED` `NOT_MEASURABLE` | 17-spec §4 |
| CredentialStatus | `PENDING_PRECHECK` `PRECHECK_PASSED` `PRECHECK_FAILED` `ACTIVE` `INVALID` | 17-spec §4 |
| QuoteStatus | `DRAFT` `SUBMITTED` `IN_REVIEW` `REJECTED` `APPROVED` `CONTRACT_CREATED` `CONVERTED` `VOID` | 10-PRD §4.1 |
| ContractStatus | `CREATED` `PENDING_SIGN` `SUPPLIER_SIGNED` `SIGNED` `ARCHIVED` `VOIDED` | 10-PRD §4.2 |
| PaymentStatus | `UNSETTLED` `PAYMENT_RECORDED` `CONFIRMED` `VOID` | 10-PRD §4.3 |
| SyncStatus | `PENDING` `SYNCING` `SYNCED` `PARTIAL` `FAILED` `ENABLED` `DISABLED` `ROLLED_BACK` `NOT_SYNCED` | 17-spec §4 + 11-PRD |
| TriggerType | `FIRST` `MANUAL` `SCHEDULED` | 17-spec §4 |
| Role | `SUPPLIER` `PROVIDER` `BIZ_OPERATOR` `TECH_OPS` `SUPER_ADMIN` | 17-spec §4 + `aap-client/src/api/auth.ts` |
| ReportResult | `PASS` `FAIL` `MANUAL_REVIEW` | 09-PRD §3 |
| Confidence | `HIGH` `MEDIUM` `LOW` | 09-PRD §2 |
| TierField | `len`（**固定**，禁 `p`） | 06-PRD R2/AC-26 |
| PriceStrategy | `OVERRIDE` `MULTIPLY` | 10-PRD §3.4 |
| WeekdayScope | `ALL` `WEEKDAY` `WEEKEND` | 10-PRD §3.3 |
| CacheParseStatus | `OK` `NO_CACHE_FIELD` | 11-PRD §4 |

## 6. 变更记录
| 2026-09-18 | `ADM-Q01` 增补 `E-1601`（报价单未审核通过不得编译）；`QT-12` 明确为**只算不落库**的预览 | 资金风险控制（偏差 D-COMPILE-02）；客户端 `quote.ts` 未接线 compile-preview，此处按 18-API 路径补齐 | 
| 日期 | 变更 | 依据 |
| --- | --- | --- |
| 2026-09-18 | `QT-03/06/07/08` 错误码勘误：资源不存在由 `E-1401` 改为 **`E-1406`(404)**；`E-1401` 严格保留给「时段区间重叠/时段非法」（HTTP 400）；`QT-08` 增补 `E-1404`（阶梯首档/末档）与 `E-1104`（If-Match 失配） | 实现期发现同一错误码承载两种 HTTP 语义会误导前端（偏差 D-API-02）；10-PRD §5.1 V11–V14 | | 2026-09-18 | 审计动作枚举新增 `QUOTE_CREATE/QUOTE_SAVE/QUOTE_SUBMIT/QUOTE_WITHDRAW/QUOTE_VOID`（12→17） | 10-PRD §7 埋点 quote_created/saved/submitted/withdrawn | 
| 2026-09-23 | 新增 **`ADM-AUTH01`**（`POST /admin/auth/sms/login`，管理端短信登录）；`AUTH-06` 明确管理端主体返回管理端档案；冻结清单 90 → **91**（管理端 41 → 42） | 运行态实测：管理端此前无登录入口，`aap-admin` 调供应商 `AUTH-02` 只得 PROVIDER 身份 → `/admin/**` 全 403 `E-1901`（人工放行 DET-06 等调不动，而报价前置 PASS 只能来自人工放行）→ 偏差 **D-AUTH-01** | 
| 2026-09-23 | 新增 **`ADM-DET01`**（`GET /admin/detection-jobs`，管理端检测任务列表）；`detection-job` 模型 +2 个**可选**字段 `provider_name`/`credential_alias`；冻结清单 98 → **99**（管理端 49 → 50） | 运行态实测：管理端无任务列表端点 → 「检测中心」KPI/表格全空、人工放行需手输任务 ID（运营无从得知）→ **放行实际不可用**，而它是 PASS 的唯一路径 → 偏差 **D-ADM-05** | 
| 2026-09-23 | 新增 **`ADM-Q03`**（`GET /admin/quotes/{id}/items`，管理端跨供应商只读报价明细）；冻结清单 97 → **98**（管理端 48 → 49） | 运行态实测：报价审核页调供应商端点 `GET /quotes/{id}/items` → 管理端令牌 403 → **审核员看不到价格只能盲审** → 偏差 **D-ADM-04** | 
| 2026-09-23 | 新增 **`ADM-PAY04`**（`POST /admin/payments` 记录打款）与 **`ADM-PAY05`**（`POST /admin/payments/{id}/void` 作废打款）；审计动作枚举 +`PAYMENT_RECORD`/`PAYMENT_VOID`；冻结清单 91 → **93**（管理端 42 → 44） | 运行态实测：`aap_payment_record` 全仓无 insert 路径 → `ADM-PAY02` 无对象可确认（total=0），合同签完后链路断开；真源 10-报价与合同结算PRD §4.3/§5.3（记录打款需凭证、VOID 作废后重录） → 偏差 **D-PAY-01** | 

- 2026-09-17 v1.0 首版：从 `18-API设计OpenAPI.md` + `aap-client` 调用点反推，冻结 90 条端点 ID
  （供应商端 49 = 客户端已消费 30 条 + 补齐 `CRED-02/06/07`、`DET-01/04/05/06`、`QT-02/05/07/11/12`、`CON-01`、`PAY-01`、`NTF-01/02`、`AUTH-04/05`；管理端 41）。
  端点表与 `tools/gen-backend-models.py` 的 `PATHS` 表逐条同源，`openapi.yaml` 由该脚本生成（禁止手改）。

### 2026-09-18（R18 · T14 批次四：ADM-P01…03、ADM-C01/02、ADM-Q02）

| 产物 | 变更 | 依据 |
| --- | --- | --- |
| 审计动作枚举 | 新增 `PROVIDER_RESUME`（12→18；生成器 `AuditAction` 同步并重跑生成 schema/openapi） | 恢复是独立的安全相关动作，复用 `PROVIDER_SUSPEND` 会让审计无法区分「谁暂停 / 谁恢复」（偏差 D-ADM-05） |
| `ADM-P02` | 暂停时写入「暂停前状态」：`aap_provider.status_before_suspend`（V8 迁移） | 偏差 D-ADM-01：恢复（ADM-P03）需回到暂停前状态，清单/ER 原本只留了暂停**时刻**（`suspended_at`） |
| `ADM-Q02` | 冻结字段级口径：`quoteIds` 旧→新、取**首单 vs 末单**、模型并集、`change_rate` 为百分数（单侧缺失/旧值 0 → null）、**不做币种换算** | 偏差 D-ADM-02（清单只写「旧值/新值/涨跌幅 A8」，PRD §5.3/§5.6 指向多单对比） |
| `ADM-Q02` | 角色取清单：`BIZ_OPERATOR` + `SUPER_ADMIN`（**不放技术运营**） | 偏差 D-ADM-03：PRD §5.6 表格含技术运营，与清单冲突 → 冲突取清单（硬约束 1） |
| 全部 90 条 | **90/90 已注册、missing 0**，`EndpointCoverageTest` 转绿，全量 204 例全绿 | R18 收口；证据 `.agents/state/evidence/green-T14-batch4.txt` |
