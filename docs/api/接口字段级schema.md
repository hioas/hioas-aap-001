# 接口字段级 schema（项目补充 · 供应商端）

> **性质**：`18-API设计OpenAPI.md` 只给了路径与通用约定（完整 153KB spec 在其 `05-架构/03-API设计-openapi.yaml`，未随卡导出）。
> 本文件是对**供应商端已实现页面**所依赖接口的**字段级补充**，字段名一律取自项目内既有真源，不新造：
>
> | 字段来源 | 依据 |
> |---|---|
> | 用量域字段 | `15-数据模型ER与数据字典.md` §`aap_usage_hourly`、`11-同步与用量统计PRD.md` §「小时用量表」「对账视图指标」 |
> | 档案域字段 | `17-零歧义执行规格spec.md` §3 实体（Provider / ProviderAccount） |
> | 路径 / 方法 / 错误结构 / 脱敏 | `18-API设计OpenAPI.md` §通用约定 |
>
> **决策（2026-09-16，用户拍板）**：JSON 字段一律 **snake_case**，与数据字典 1:1 同名，不做 camelCase 转换 —— 消除"字典名 ↔ 响应名"两套命名的经典不一致。

## 0. 通用约定（所有供应商端接口）

| 项 | 约定 |
|---|---|
| 前缀 | `/api/v1` |
| 鉴权 | `Authorization: Bearer <jwt>`（supplier：`role=PROVIDER`） |
| 响应包体 | `{"code":"0|E-xxxx","message":"...","data":{...},"traceId":"..."}` |
| 分页 | 请求 `page`（默认 1）/ `pageSize`（默认 20，上限 200）；深分页改 `cursor`。响应 `data:{list:[],page,pageSize,total}` |
| 幂等 | 非幂等写支持 `Idempotency-Key`（24h） |
| 乐观锁 | 需并发保护的写支持 `If-Match` |
| 时间 | RFC3339 **UTC**（`2026-09-16T00:00:00Z`）；小时桶为**整点** |
| 金额 | `numeric(18,6)`，单位 **USD**；单价单位 **USD / 1M tokens** |
| 脱敏 | `apiKeyMask` = `sk-****abcd`（R-05）；手机号 = `138****8888`（R-48）；后端不回明文 |
| 缺字段 | **一律回 null 或省略，前端显示占位符**；禁止用 0 冒充"没有数据"（例外：`cache_parse_status=NO_CACHE_FIELD` 明确记 0，依据 11-PRD U2） |

## 1. GET /usage/summary — 供应商用量概览

**用途**：序号 2 工作台（`pages/workbench/index.vue`）、序号 22 用量页。
**作用域**：默认本人 provider；管理端另有 `/admin/usage/*`（`18-API` Usage Tag）。

| 字段 | 类型 | 单位 | 说明 / 来源 |
|---|---|---|---|
| `provider_id` | string | — | 供应商主键 |
| `stat_from` / `stat_to` | string | RFC3339 | 统计窗口（半开区间 `[from, to)`） |
| `request_count` | integer | 次 | 请求数（字典 `request_count`） |
| `prompt_tokens` | integer | token | 输入词元（字典 `prompt_tokens`） |
| `completion_tokens` | integer | token | 输出词元（字典 `completion_tokens`） |
| `total_tokens` | integer | token | 总量（字典 `total_tokens`）；图例百分比的分母 |
| `cache_read_tokens` | integer | token | 缓存读（字典 `cache_read_tokens`/`cr`） |
| `cache_write_tokens` | integer | token | 缓存写（字典 `cache_write_tokens`/`cc`） |
| `cache_write_1h_tokens` | integer | token | 1h 缓存写（字典 `cache_write_1h_tokens`/`cc1h`） |
| `image_input_tokens` | integer | token | 图片输入（11-PRD 小时表字段） |
| `audio_input_tokens` | integer | token | 音频输入（11-PRD 小时表字段） |
| `video_input_tokens` | integer | token | **Aap 扩展**：11-PRD 未列视频字段，设计稿（page-2-b）要求"视频"图例 → 后端需补同类字段；未提供时前端占位 |
| `cache_hit_rate` | number | 0–1 | 缓存命中率（11-PRD 对账指标）。**小数比率**，前端 `formatPercent` 渲染为百分比 |
| `cache_parse_rate` | number | 0–1 | 缓存可解析率（11-PRD U2/U8、A14；`cache_parse_status` 聚合） |
| `quota_raw` | number | quota | 计费额度（字典 `quota_raw`/`quota`） |
| `cost_usd` | number | USD | 折算金额（字典 `cost_usd`） |
| `amount_total` | number | USD | 账单口径合计（工作台"合计"行）；缺省时前端按 `models[].amount` 求和 |
| `mom_rate` | number | 0–1 | 环比（MoM）变化率，可负；前端带符号渲染 |
| `actual_unit_price` | number | USD/1M | 实际单价（11-PRD 对账指标） |
| `deviation_rate` | number | 0–1 | 差异率 `(实际-报价)/报价`；绝对值 >0.05 触发告警（11-PRD 阈值 ±5%） |
| `tier_distribution` | object | — | 档位分布：`{"t1_base":120000,"t2_long":8000,...}`（键=编译档位名，见 17-spec §8） |
| `models` | array\<UsageModel\> | — | 按时段聚合的模型明细（下表） |

**UsageModel**

| 字段 | 类型 | 单位 | 说明 |
|---|---|---|---|
| `model_name` | string | — | 模型名（字典 `model_name`） |
| `request_count` | integer | 次 | 该模型请求数 |
| `total_tokens` | integer | token | 该模型词元量 |
| `amount` | number | USD | 该模型折算金额（前端排序/占比条依据） |

## 2. GET /usage/hourly — 分时用量（峰谷着色）

**用途**：序号 22 用量概览、管理端用量页。
**查询**：`from` / `to`（RFC3339）、`model`（可选）、`group`（可选）、`page` / `pageSize`。

`data = { list: [UsageHourlyBucket], page, pageSize, total }`

**UsageHourlyBucket**（= `aap_usage_hourly` 字典字段，仅透出供应商可见子集）

| 字段 | 类型 | 说明 |
|---|---|---|
| `stat_hour` | string | 小时整点（UTC）；唯一键组成部分 |
| `channel_id` / `channel_name` | string | 渠道（供应商端只回自己渠道） |
| `model_name` / `group_name` | string | 维度键（唯一键组成部分） |
| `request_count` | integer | 请求数 |
| `prompt_tokens` / `completion_tokens` / `total_tokens` | integer | 词元 |
| `cache_read_tokens` / `cache_write_tokens` / `cache_write_1h_tokens` | integer | 缓存三件套 |
| `image_input_tokens` / `audio_input_tokens` | integer | 多模态输入 |
| `quota_raw` | number | quota |
| `cost_usd` | number | USD |
| `cache_parse_status` | string | `OK` \| `NO_CACHE_FIELD`（U2：不可解析记 0，**不臆造数值**） |
| `source` | string | `LOG_API` \| `LOG_DB`（字典 `source`） |

## 3. GET /provider/profile — 供应商档案

**用途**：序号 10 档案编辑、序号 10.1 供应商档案、序号 2 工作台抬头。

| 字段 | 类型 | 说明 / 来源 |
|---|---|---|
| `provider_id` | string | 主键 |
| `provider_code` | string | `AAP-P-{6位}`（17-spec §3 Provider） |
| `short_name` | string | 简称（渠道名 `AAP-{short_name}-{seq}` 使用，R-36~38） |
| `company_name` | string | 企业全称 |
| `uscc` | string | 统一社会信用代码 |
| `contact` | object | `{name, phone_masked, email}`；phone 一律 `138****8888` 形态（R-48） |
| `qualification_files` | array\<FileAsset\> | `{file_id, file_name, size, uploaded_at, type}`；上传走 `POST /provider/qualifications` |
| `status` | string | `ProviderStatus` 枚举（17-spec §4，12 态：PENDING_CREDENTIAL … TERMINATED） |
| `recheck_interval_days` | integer | 复测间隔（默认 30，AC-49） |
| `manual_override` | boolean | 是否人工放行 |
| `override_reason` | string \| null | 人工放行理由；`manual_override=true` 时**必填**（R-47a） |
| `account` | object | `{phone_masked, role, wx_bound}`；`role∈{PROVIDER}`（17-spec §4 Role） |
| `created_at` / `updated_at` | string | RFC3339 UTC |

**写接口**：`PUT /provider/profile`（幂等：`Idempotency-Key`；并发：`If-Match: <updated_at 或 etag>`），请求体为上述可写子集（`company_name`/`uscc`/`contact`/`recheck_interval_days`），校验失败 `E-1001`。

## 4. 错误码（本文件涉及）

| 码 | 场景 |
|---|---|
| `E-1001` | 参数校验失败（含手机号 `^1[3-9]\d{9}$`、验证码 6 位、uscc 格式） |
| `E-1104` | 凭证/档案唯一性冲突（如 uscc 重复） |
| `E-1901` / `E-1902` / `E-1903` | 权限不足 / 未认证 / 限流 |
| `E-1801` | 用量聚合失败（接口降级为最近可用窗口，**不返回 0 冒充**） |
| `E-2001` | 内部错误 |

## 5. 前端落地约定（aap-client）

- HTTP 层：`src/api/http.ts`（`/api/v1` + 包体校验 + `E-1902` 清 token + 网络层 `E-2001`）。
- 视图模型：`src/utils/workbench-model.ts` 只做"展示口径映射"，字段缺失 → `PLACEHOLDER`，不编数字。
- 百分比**一律由真实数值计算**（`percentOf(value,total)`），不得沿用设计稿里的硬编码百分比：
  page-2-b 设计稿图例"音频 6% + 视频 6%"与总量口径不一致（合计 106%），已按此规则归一到真实占比。
- 金额/数量/百分比格式化：`src/utils/format.ts`（`formatTokens` 3.86B 千分位 K/M/B、`formatAmount` 千分位、`formatPercent` 小数→百分比）。

---

**变更记录**
- 2026-09-16 首版：由用户决定「补字段级 schema」后编写；覆盖供应商端在用接口 `/usage/summary`、`/usage/hourly`、`/provider/profile`。
