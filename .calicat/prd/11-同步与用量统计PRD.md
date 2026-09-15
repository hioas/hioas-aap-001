# 同步与用量统计PRD

# PRD — 同步与用量统计

> 对应模块 M10（计费编译）、M11（new-api 同步）、M12（用量统计）。new-api 集成零源码改动。
> **红线**：编译产物未经模拟求值校验，禁止写入 new-api 生产环境。

## 1. 目标与范围

| 模块             | 本期范围                         | 明确不做         |
| -------------- | ---------------------------- | ------------ |
| M10 计费编译       | 报价→billingexpr 编译、三道闸门、产物快照  | 供应商侧可见编译细节   |
| M11 new-api 同步 | 建渠道/改价/启停、幂等、回读、重试回滚、日志审计、灰度 | new-api 源码改造 |
| M12 用量统计       | 小时级聚合、自建用量表（含缓存）、对账视图        | 资金结算         |

集成路径（全部走既有管理 API）：建渠道 `POST /api/channel/`（ChannelSensitiveWrite）；改渠道 `PUT /api/channel/`；写价格 option `billing_setting.billing_expr[model]`；批量启停 `tag/enabled|disabled`；同步模型 `POST /api/models/sync_upstream`；用量聚合 `SumUsedQuota(...channel...)`。

## 2. M10 计费编译

### 三道闸门

| 闸门 | 名称     | 通过条件           | 不通过后果            |
| -- | ------ | -------------- | ---------------- |
| ①  | 编译     | 边界检测无冲突，表达式可编译 | 拒绝，产物不入库         |
| ②  | 模拟求值校验 | 样例向量实算==预期价格   | 拒绝写入 new-api（红线） |
| ③  | 人工确认   | 运营三栏页点击确认      | 保持待确认，不写生产       |

### 编译规则映射（引用商业编译规则）

R1 基础价 → `v1: tier("base", p*2.5 + c*15 + cr*0.25)`；R2 阶梯（★必须用 len）→ `len <= 512000 ? tier(...) : ...`；R3 峰谷 → `(hour>=9 && <12 || ...) ? tier("peak",*2) : tier("offpeak",*1)`；R4 组合外层 len 内层 hour；R5 请求级 `|||`；R6 多模型 N 条独立表达式。

编译红线：系数是真实 \$/1M 单价；阶梯必须用 len；p/c 自动排除避免重复计费。

### 边界冲突检测（闸门①）

B1 时段重叠；B2 时段 start\<end；B3 阶梯空洞/重叠；B4 首档 min=0 末档 max=null；B5 倍率≤0/NaN；B6 单价非负；B7 tier\_field=len。

### 模拟校验用例（闸门②）

基础（prompt=1000/completion=500）；缓存命中（p=800+cr=200 无重复计费）；阶梯边界（len=512000 vs 512001）；时段边界（09:00/08:59/12:00/18:00 半开区间）；组合（len=600000@10:00 命中 t1.peak）；多模态。

### 编译产物结构

含 compiled\[]（model/expr\_version/expr/tier\_labels/source\_hash/verified/verify\_report）、gate\_status（COMPILED|VERIFIED|CONFIRMED|REJECTED）、previous\_expr 旧快照。落库表 compile\_artifact。

## 3. M11 new-api 同步

### 渠道字段映射

`name`=AAP-{简称}-{序号}；`key`=apikey（解密后写入，日志脱敏）；`base_url`；`models`=逗号分隔；`group`=定价分组；`tag`=aap-provider-{id}；`status`=打款确认后置 1；`setting` 不覆盖。

### 幂等键设计

建渠道 `sha256(provider_id|ADD_CHANNEL|channel_name)`；写价 `sha256(provider_id|WRITE_EXPR|model|source_hash)`（source\_hash 不变跳过）；改渠道 `sha256(channel_id|UPDATE_CHANNEL|payload_hash)`；启停 `sha256(provider_id|TAG_STATUS|目标状态)`。

读前写后三段式：读前按自然键查询现值 → 写入 → 回读校验比对，不一致告警+重试。

### 状态机（渠道上架）

`PENDING→SYNCING→（SYNCED | PARTIAL→重试/回滚/转人工）`；`SYNCED→ENABLED→（DISABLED⇄ENABLED）`；`ROLLED_BACK→PENDING`。

### 灰度策略

阶段一 DRY\_RUN（只编译不调 new-api）；阶段二 REVIEW\_THEN\_APPLY（人工确认后执行，默认）；阶段三 AUTO\_APPLY（白名单供应商自动）。**闸门②永不跳过。**

### 同步日志 sync\_log

sync\_id/provider\_id/channel\_id/operation/idempotency\_key/request\_payload（脱敏）/response\_payload/result/readback\_equal/attempt\_no/error/operator\_id/created\_at。

## 4. M12 用量统计

### 数据缺口 F8

new-api Log 表无独立缓存 token 字段（在 Other JSON 内）。方案 C：AAP 自建小时用量表，按小时拉日志解析落库，不污染 new-api。

### 小时用量表 usage\_hourly

`stat_hour`（小时截断）/`channel_id`/`channel_name`/`provider_id`/`model_name`/`group_name`/`request_count`/`prompt_tokens`/`completion_tokens`/`total_tokens`/`cache_read_tokens`（cr）/`cache_write_tokens`（cc）/`cache_write_1h_tokens`（cc1h）/`image_input_tokens`/`audio_input_tokens`/`quota`/`cost_usd`/`tier_distribution`/`cache_parse_status`/`batch_id`。

唯一键 `(stat_hour, channel_id, model_name, group_name)` UPSERT 幂等。缓存字段来源解析 Log.Other（OpenAI cached\_tokens / Claude cache\_read\_input\_tokens）；解析失败记 NO\_CACHE\_FIELD 不臆造数值。

### 对账视图指标

请求数、输入/输出 token、缓存读/写 token、缓存命中率、计费额度 quota、折算金额 cost\_usd、实际单价、差异率（实际-报价）/报价（阈值 ±5% 告警）、档位分布、缓存可解析率。对账维度：供应商×渠道×模型×小时。

## 5. 校验、重试与异常

### 同步失败重试

1 次立即 → 30s → 2min → 8min → 30min；鉴权类（401/403）不重试直接转 MANUAL；耗尽后 MANUAL 告警。

### 降级动作

渠道已建价格失败→保持待启用重试价格/删除回滚；价格已写渠道失败→回滚 option 恢复 previous\_expr；回读不一致→转 MANUAL；new-api 不可达→重试队列不阻塞主流程；多模型部分失败→单模型回滚。

### 用量异常

U1 窗口重叠/漏点→UPSERT 幂等补数；U2 无缓存字段→NO\_CACHE\_FIELD 记 0；U3 Other 结构变化→多字段兜底+告警；U5 渠道未映射→provider\_id 置空告警；U8 大量日志→分页限速。

## 6. 埋点与指标

compile\_started/succeeded/verify\_failed（关键质量指标）；sync\_success/failed/rolled\_back/skipped/readback\_mismatch；usage\_aggregation\_failed；cache\_parse\_unavailable。质量指标：compile\_verify\_failed 占比 <5%，readback\_mismatch 次数 =0。

## 7. 验收标准

A1 多模型 N 条独立表达式单模型失败不影响其他；A2 编译失败定位到字段；A3 未过模拟求值无法写入 new-api；A4 六类校验用例可跑；A5 建渠道幂等；A6 source\_hash 不变跳过；A7 回读不一致告警重试；A8 鉴权失败不重试转 MANUAL；A9 部分失败可回滚保留快照；A10 tag 批量启停；A11 同步日志脱敏无明文；A12 灰度三阶段可切换；A13 小时表幂等 UPSERT；A14 缓存字段落库+不可解析标 NO\_CACHE\_FIELD；A15 对账指标正确定位；A16 用量任务故障不阻塞主流程。
