# data-model · 进件自动化数据模型增量

> 配套 `spec.md`。本文只写**本次新增/变更**的表；未提及的表沿用
> `.calicat/prd/15-数据模型ER与数据字典.md`（53 张）与 `docs/backend/01-ER数据模型.md`。
> 命名与类型约定与既有完全一致：前缀 `aap_`、主键 `bigint` 雪花、`timestamptz` UTC、
> 金额 `numeric(20,8)`、软删 `deleted boolean`、乐观锁 `version int`、逻辑外键（不建 DB 级 FK）、
> 审计字段 `created_at/updated_at/created_by/updated_by`。

---

## 1. 变更总览

| 类型 | 表 | 说明 |
| --- | --- | --- |
| **改** | `aap_channel_binding` | 渠道粒度从「供应商」改为「供给单元（模型 × 供应商）」 |
| **增** | `aap_supply_unit` | 供给单元聚合根：模型 × 供应商 的最小组合 |
| **增** | `aap_model_catalog` | 平台模型目录（FR-3.1） |
| **增** | `aap_model_price` | 模型价格表：基准价/对外价 + 版本 + 生效时间（FR-3.2） |
| **增** | `aap_channel_price` | 渠道价格表：`(渠道 × 模型) → 生效价` + 来源 + 回读状态（FR-4） |
| **增** | `aap_routing_policy` | 模型级调度策略（priority/weight 规则）（FR-6.4） |
| **增** | `aap_quality_feedback` | 渠道实测质量反馈（驱动调权）（FR-7.1） |
| **增** | `aap_config_batch` / `aap_config_batch_item` | 批量配置批次与明细（FR-2.5 / FR-6.2） |
| **增** | `aap_automation_assessment` | 自动化等级判定记录（FR-1.10 / R-60） |
| **增** | `aap_price_drift` | 价格漂移记录（FR-7.2 / R-63） |
| **增** | `aap_intake_run` | 进件流水线运行实例（FR-1.7/1.8/1.9） |

表总数：53 → **64**。

---

## 2. 变更：`aap_channel_binding`

**变更点**：一条渠道绑定一个**供给单元**（单模型），而非一个供应商的全部模型。

```sql
-- 新增列
ALTER TABLE aap_channel_binding
  ADD COLUMN supply_unit_id bigint,              -- 供给单元（模型 × 供应商）
  ADD COLUMN model_name     varchar(128),        -- 冗余存该渠道的唯一模型（便于查询与回读校验）
  ADD COLUMN granularity    varchar(16) NOT NULL DEFAULT 'PER_MODEL',  -- PER_MODEL | PER_PROVIDER
  ADD COLUMN routing_priority bigint,            -- 回读缓存：写入时的 priority
  ADD COLUMN routing_weight   int;               -- 回读缓存：写入时的 weight

-- 唯一约束：同一供给单元只能有一条 PER_MODEL 渠道
CREATE UNIQUE INDEX uq_binding_supply_unit
  ON aap_channel_binding (supply_unit_id)
  WHERE deleted = false AND granularity = 'PER_MODEL';

-- 渠道名全局唯一（跨粒度，防模型级渠道与合并渠道撞名）——沿用既有唯一性并补充说明
-- channel_name 已是唯一列；本特性要求命名规则见 spec §3.3
```

**既有列语义收紧**：

| 列 | 旧语义 | 新语义 |
| --- | --- | --- |
| `models` | 逗号分隔的模型列表（多值） | **单值**（PER_MODEL 下恰为一个模型）；合并模式下仍多值 |
| `channel_name` | `AAP-{short_code}-{seq}` | PER_MODEL：`AAP-{short_code}-{model_slug}`；PER_PROVIDER：沿用旧规则 |
| `tag` | `= provider_code` | 不变（仍按供应商打标，支撑批量启停） |

**不变式（应用层校验，写进 `ChannelConfigValidator`）**：

- `granularity = PER_MODEL` ⇒ `models` 恰好为 1 个模型，且与 `supply_unit.model_name` 一致（R-56）。
- `channel_name` 与 `(short_code, model_name)` 一一对应：反解失败视为数据损坏，启动自检告警。
- 合并渠道的 `channel_name` 不得与任何 PER_MODEL 渠道同名（R-54/AC-20）。

---

## 3. 新增：`aap_supply_unit`（供给单元）

本特性的**核心聚合**：把「某供应商的某模型」提升为一等对象。

```sql
CREATE TABLE aap_supply_unit (
  id                bigint PRIMARY KEY,
  provider_id       bigint       NOT NULL,
  credential_id     bigint       NOT NULL,
  model_name        varchar(128) NOT NULL,
  model_slug        varchar(160) NOT NULL,        -- 渠道名用 slug（spec §3.3）
  -- 状态与质量画像
  status            varchar(32)  NOT NULL,        -- PENDING/CONFIGURING/ONLINE/DEGRADED/SUSPENDED/OFFLINE
  detect_total_score  numeric(6,2),               -- 最近一次检测总分（快照）
  detect_confidence   varchar(16),                -- HIGH/MEDIUM/LOW
  quality_score     numeric(6,2),                 -- 由 quality_feedback 聚合出的运行质量分
  -- 调度画像（写入网关的期望值，实际值以渠道回读为准）
  routing_priority  bigint       NOT NULL DEFAULT 0,
  routing_weight    int          NOT NULL DEFAULT 0,
  auto_ban_enabled  boolean      NOT NULL DEFAULT true,
  -- 关联
  binding_id        bigint,                       -- 对应渠道绑定（PER_MODEL 时 1:1）
  granularity       varchar(16)  NOT NULL DEFAULT 'PER_MODEL',
  -- 审计
  version           int          NOT NULL DEFAULT 0,
  created_at        timestamptz  NOT NULL,
  updated_at        timestamptz  NOT NULL,
  created_by        bigint,
  updated_by        bigint,
  deleted           boolean      NOT NULL DEFAULT false
);

CREATE UNIQUE INDEX uq_supply_unit_provider_model
  ON aap_supply_unit (provider_id, model_name) WHERE deleted = false;
CREATE INDEX idx_supply_unit_model_status ON aap_supply_unit (model_name, status) WHERE deleted = false;
CREATE INDEX idx_supply_unit_provider    ON aap_supply_unit (provider_id)      WHERE deleted = false;
```

**不变式**：

- `(provider_id, model_name)` 唯一（同一供应商同一模型只有一个供给单元）。
- `status = ONLINE` ⇒ 必须存在 `binding_id` 且其回读校验通过。
- `quality_score` 只能由 `aap_quality_feedback` 的聚合任务写入，禁止外部直改（可解释性 C-07/R-64）。

---

## 4. 新增：`aap_model_catalog`（平台模型目录，FR-3.1）

```sql
CREATE TABLE aap_model_catalog (
  id                bigint PRIMARY KEY,
  model_name        varchar(128) NOT NULL,        -- 平台标准名（对外唯一可调用名）
  vendor            varchar(64),                  -- OpenAI/Anthropic/Google/… 或 SELF_HOSTED
  display_name      varchar(128),
  capability_tags   jsonb NOT NULL DEFAULT '[]',  -- ["text","vision","tool_call","reasoning"]
  context_window    int,
  max_output_tokens int,
  modality          jsonb NOT NULL DEFAULT '{}',  -- 输入/输出模态
  status            varchar(16) NOT NULL,         -- ACTIVE/DEPRECATED/RETIRED
  aliases           jsonb NOT NULL DEFAULT '[]',  -- 供应商侧的等价模型名（用于自动映射）
  upstream_meta     jsonb NOT NULL DEFAULT '{}',  -- 从网关/上游同步来的原始元数据
  version           int NOT NULL DEFAULT 0,
  created_at        timestamptz NOT NULL,
  updated_at        timestamptz NOT NULL,
  updated_by        bigint,
  deleted           boolean NOT NULL DEFAULT false
);
CREATE UNIQUE INDEX uq_model_catalog_name ON aap_model_catalog (model_name) WHERE deleted = false;
CREATE INDEX idx_model_catalog_status ON aap_model_catalog (status) WHERE deleted = false;
```

---

## 5. 新增：`aap_model_price`（模型价格表，FR-3.2）

平台视角的价格，**版本化 + 生效时间**，保留历史。

```sql
CREATE TABLE aap_model_price (
  id                bigint PRIMARY KEY,
  model_id          bigint       NOT NULL,        -- → aap_model_catalog.id
  price_version     int          NOT NULL,        -- 同一模型的价格版本号，单调递增
  -- 八大单价（与报价单口径一致，USD / 1M tokens）
  input_price       numeric(20,8) NOT NULL DEFAULT 0,
  output_price      numeric(20,8) NOT NULL DEFAULT 0,
  cache_read_price  numeric(20,8) NOT NULL DEFAULT 0,
  cache_write_price numeric(20,8) NOT NULL DEFAULT 0,
  cache_write_1h_price numeric(20,8) NOT NULL DEFAULT 0,
  image_price       numeric(20,8) NOT NULL DEFAULT 0,
  audio_price       numeric(20,8) NOT NULL DEFAULT 0,
  img_output_price  numeric(20,8) NOT NULL DEFAULT 0,
  -- 价格角色
  price_role        varchar(16) NOT NULL,         -- COST_BENCHMARK（基准）/ SELLING（对外）/ REFERENCE（参考）
  currency          varchar(8)  NOT NULL DEFAULT 'USD',
  -- 生效与来源
  effective_from    timestamptz NOT NULL,
  effective_to      timestamptz,                  -- null = 当前生效
  source            varchar(32) NOT NULL,         -- MANUAL/UPSTREAM_SYNC/QUOTE_DERIVED
  source_ref        varchar(128),                 -- 同步批次号 / 报价单号
  markup_rate       numeric(10,6),                -- 对外价相对基准价的加成率（可空）
  remark            varchar(255),
  created_at        timestamptz NOT NULL,
  created_by        bigint,
  deleted           boolean NOT NULL DEFAULT false
);
-- 同模型同角色同版本唯一；同角色在任一时刻至多一条生效（应用层 + 部分唯一索引）
CREATE UNIQUE INDEX uq_model_price_role_version
  ON aap_model_price (model_id, price_role, price_version) WHERE deleted = false;
CREATE UNIQUE INDEX uq_model_price_role_effective
  ON aap_model_price (model_id, price_role)
  WHERE deleted = false AND effective_to IS NULL;
CREATE INDEX idx_model_price_effective_from ON aap_model_price (effective_from);
```

**不变式**：同一 `(model_id, price_role)` 在任一时刻最多一条 `effective_to IS NULL`（当前生效）；
调价 = 旧记录写 `effective_to` + 新记录插入（**只增不改**，保证历史可审计）。

---

## 6. 新增：`aap_channel_price`（渠道价格表，FR-4）★

采购视角：`(渠道 × 模型) → 生效价`。它是**对账基准**，也是比价矩阵的数据源。

```sql
CREATE TABLE aap_channel_price (
  id                bigint PRIMARY KEY,
  supply_unit_id    bigint       NOT NULL,
  binding_id        bigint       NOT NULL,        -- → aap_channel_binding.id
  channel_id        bigint,                       -- 网关侧渠道 id（回读填充）
  provider_id       bigint       NOT NULL,
  model_name        varchar(128) NOT NULL,
  -- 生效价（来自编译产物，禁止手工直改 —— R-62）
  input_price       numeric(20,8) NOT NULL DEFAULT 0,
  output_price      numeric(20,8) NOT NULL DEFAULT 0,
  cache_read_price  numeric(20,8) NOT NULL DEFAULT 0,
  cache_write_price numeric(20,8) NOT NULL DEFAULT 0,
  cache_write_1h_price numeric(20,8) NOT NULL DEFAULT 0,
  image_price       numeric(20,8) NOT NULL DEFAULT 0,
  audio_price       numeric(20,8) NOT NULL DEFAULT 0,
  img_output_price  numeric(20,8) NOT NULL DEFAULT 0,
  -- 来源链（可追溯到报价单与编译产物）
  quote_id          bigint,
  quote_version     int,
  compilation_id    bigint,
  model_expression_id bigint,                     -- → aap_model_expression.id
  price_expr        text,                         -- 生效表达式快照
  source_hash       varchar(64),                  -- 编译产物 source_hash（幂等依据）
  -- 生效与同步状态
  effective_from    timestamptz NOT NULL,
  effective_to      timestamptz,
  sync_status       varchar(24) NOT NULL,         -- PENDING/SYNCED/READBACK_MISMATCH/FAILED
  readback_hash     varchar(64),
  readback_at       timestamptz,
  readback_payload  jsonb,                        -- 回读的定价片段（脱敏）
  currency          varchar(8) NOT NULL DEFAULT 'USD',
  created_at        timestamptz NOT NULL,
  updated_at        timestamptz NOT NULL,
  created_by        bigint,
  updated_by        bigint,
  deleted           boolean NOT NULL DEFAULT false
);
CREATE UNIQUE INDEX uq_channel_price_unit_effective
  ON aap_channel_price (supply_unit_id) WHERE deleted = false AND effective_to IS NULL;
CREATE INDEX idx_channel_price_model   ON aap_channel_price (model_name, effective_to IS NULL);
CREATE INDEX idx_channel_price_provider ON aap_channel_price (provider_id);
CREATE INDEX idx_channel_price_sync    ON aap_channel_price (sync_status) WHERE sync_status <> 'SYNCED';
```

**派生视图（只读，供 FR-4.3/4.4）**：

| 视图 | 用途 |
| --- | --- |
| `v_channel_price_matrix` | `模型 × 供应商 → 生效输入/输出价` 横向矩阵（比价） |
| `v_model_margin` | 渠道价（采购）与模型对外价之差，按模型/供应商聚合（毛利） |
| `v_model_supply_coverage` | 每个模型的在架供应商数与质量分（FR-3.5 / 供给覆盖守护 FR-7.4） |

---

## 7. 新增：`aap_routing_policy`（模型级调度策略，FR-6.4）

```sql
CREATE TABLE aap_routing_policy (
  id                bigint PRIMARY KEY,
  model_name        varchar(128) NOT NULL,
  group_name        varchar(64)  NOT NULL DEFAULT 'default',
  strategy          varchar(24)  NOT NULL,        -- PRIORITY_FIRST / WEIGHTED_RANDOM / COST_FIRST / QUALITY_FIRST
  priority_rule     jsonb NOT NULL DEFAULT '{}',  -- 如 {"by":"provider_tier","map":{"ORIGINAL":100,"RESELLER":50}}
  weight_rule       jsonb NOT NULL DEFAULT '{}',  -- 如 {"by":"quality_score","min":1,"max":100}
  min_available_providers int NOT NULL DEFAULT 2, -- 低于则触发供给覆盖告警（FR-7.4）
  enabled           boolean NOT NULL DEFAULT true,
  version           int NOT NULL DEFAULT 0,
  created_at        timestamptz NOT NULL,
  updated_at        timestamptz NOT NULL,
  updated_by        bigint,
  deleted           boolean NOT NULL DEFAULT false
);
CREATE UNIQUE INDEX uq_routing_policy_model_group
  ON aap_routing_policy (model_name, group_name) WHERE deleted = false;
```

---

## 8. 新增：`aap_quality_feedback`（质量反馈，FR-7.1）

```sql
CREATE TABLE aap_quality_feedback (
  id                bigint PRIMARY KEY,
  supply_unit_id    bigint       NOT NULL,
  binding_id        bigint       NOT NULL,
  channel_id        bigint,
  stat_hour         timestamptz  NOT NULL,        -- UTC 整点（与用量桶同口径）
  request_count     bigint NOT NULL DEFAULT 0,
  success_count     bigint NOT NULL DEFAULT 0,
  error_count       bigint NOT NULL DEFAULT 0,
  timeout_count     bigint NOT NULL DEFAULT 0,
  latency_p50_ms    int,
  latency_p95_ms    int,
  ttft_p50_ms       int,
  error_rate        numeric(8,6),
  quality_score     numeric(6,2),                 -- 本小时综合质量分
  source            varchar(24) NOT NULL,         -- GATEWAY_METRIC / DETECTION / PROBE
  collected_at      timestamptz NOT NULL
);
CREATE UNIQUE INDEX uq_quality_feedback_unit_hour
  ON aap_quality_feedback (supply_unit_id, stat_hour, source);
CREATE INDEX idx_quality_feedback_hour ON aap_quality_feedback (stat_hour);
```

**用途**：聚合为 `aap_supply_unit.quality_score` → 驱动 `weight`（INNOV-4）。
`weight` 的映射公式见 spec Q-5（待业务确定，先做成可配权重表）。

---

## 9. 新增：`aap_config_batch` / `aap_config_batch_item`（批量配置，FR-2.5 / FR-6.2）

```sql
CREATE TABLE aap_config_batch (
  id                bigint PRIMARY KEY,
  batch_no          varchar(64)  NOT NULL,        -- CFG-2026-0001
  batch_type        varchar(24)  NOT NULL,        -- ADD_CHANNEL/UPDATE_CHANNEL/WRITE_PRICE/RECONFIG/OFFLINE/ENABLE/DISABLE
  mode              varchar(16)  NOT NULL,        -- DRY_RUN / APPLY
  trigger_source    varchar(24)  NOT NULL,        -- INTAKE_AUTO / ADMIN_MANUAL / POLICY_CHANGE / CREDENTIAL_UPDATE
  status            varchar(24)  NOT NULL,        -- PENDING/RUNNING/PARTIAL/SUCCEEDED/FAILED/CANCELLED
  total_count       int NOT NULL DEFAULT 0,
  succeeded_count   int NOT NULL DEFAULT 0,
  failed_count      int NOT NULL DEFAULT 0,
  mismatch_count    int NOT NULL DEFAULT 0,       -- 回读不一致数
  rate_limit_per_sec int NOT NULL DEFAULT 5,      -- R-57
  diff_payload      jsonb,                        -- dry-run 产出的差异清单
  operator_id       bigint,
  started_at        timestamptz,
  finished_at       timestamptz,
  created_at        timestamptz NOT NULL
);
CREATE UNIQUE INDEX uq_config_batch_no ON aap_config_batch (batch_no);

CREATE TABLE aap_config_batch_item (
  id                bigint PRIMARY KEY,
  batch_id          bigint NOT NULL,
  supply_unit_id    bigint,
  provider_id       bigint,
  model_name        varchar(128),
  action            varchar(24) NOT NULL,         -- CREATE/UPDATE/SKIP/ENABLE/DISABLE/DELETE
  status            varchar(24) NOT NULL,         -- PENDING/RUNNING/SUCCEEDED/FAILED/MISMATCH/ROLLED_BACK
  idempotency_key   varchar(128),
  request_summary   jsonb,                        -- 脱敏（key 一律以 mask 表示）
  response_summary  jsonb,
  readback_equal    boolean,
  readback_diff     jsonb,
  attempt_count     int NOT NULL DEFAULT 0,
  last_error        varchar(512),
  created_at        timestamptz NOT NULL,
  updated_at        timestamptz NOT NULL
);
CREATE UNIQUE INDEX uq_config_batch_item_idem ON aap_config_batch_item (idempotency_key);
CREATE INDEX idx_config_batch_item_batch ON aap_config_batch_item (batch_id, status);
```

**不变式**：

- `idempotency_key` 全局唯一（C-11 沿用的幂等纪律）。
- `request_summary` 与 `response_summary` 必须脱敏（R-58 / AC-18）。
- dry-run 批次**不得**产生任何网关侧写入（AC-10）。

---

## 10. 新增：`aap_automation_assessment`（自动化等级判定，FR-1.10 / R-60）

```sql
CREATE TABLE aap_automation_assessment (
  id                bigint PRIMARY KEY,
  intake_run_id     bigint,
  provider_id       bigint NOT NULL,
  level             varchar(8) NOT NULL,          -- L0/L1/L2/L3
  factor_snapshot   jsonb NOT NULL,               -- {provider_type, detect_result, confidence, model_risk, amount}
  rule_version      varchar(32) NOT NULL,         -- 风险矩阵版本
  reason            varchar(512) NOT NULL,        -- 可读原因（R-64）
  decided_by        varchar(24) NOT NULL,         -- SYSTEM / ADMIN
  operator_id       bigint,
  created_at        timestamptz NOT NULL
);
CREATE INDEX idx_automation_assessment_provider ON aap_automation_assessment (provider_id, created_at DESC);
```

---

## 11. 新增：`aap_price_drift`（价格漂移，FR-7.2 / R-63）

```sql
CREATE TABLE aap_price_drift (
  id                bigint PRIMARY KEY,
  supply_unit_id    bigint NOT NULL,
  model_name        varchar(128) NOT NULL,
  effective_input_price  numeric(20,8),           -- 渠道价格表生效价
  observed_input_price   numeric(20,8),           -- 上游实测/同步价
  drift_rate        numeric(10,6),                -- (observed - effective) / effective
  threshold_rate    numeric(10,6) NOT NULL DEFAULT 0.05,
  severity          varchar(16) NOT NULL,         -- WARN / CRITICAL
  source            varchar(32) NOT NULL,         -- UPSTREAM_SYNC / BILLING_RECON / MANUAL
  action_taken      varchar(32),                  -- NONE / WEIGHT_DOWN / DISABLED / ALERT_ONLY
  action_reason     varchar(512),
  detected_at       timestamptz NOT NULL,
  resolved_at       timestamptz,
  resolved_by       bigint
);
CREATE INDEX idx_price_drift_open ON aap_price_drift (detected_at DESC) WHERE resolved_at IS NULL;
```

---

## 12. 新增：`aap_intake_run`（进件流水线实例，FR-1.7/1.8/1.9）

```sql
CREATE TABLE aap_intake_run (
  id                bigint PRIMARY KEY,
  run_no            varchar(64) NOT NULL,         -- INK-2026-0001
  provider_id       bigint NOT NULL,
  current_stage     varchar(32) NOT NULL,         -- CREDENTIAL/PRECHECK/DETECTION/QUOTE/REVIEW/CONTRACT/PAYMENT/CONFIG/PUBLISH
  stage_status      varchar(24) NOT NULL,         -- PENDING/RUNNING/BLOCKED/DONE/FAILED/SKIPPED
  automation_level  varchar(8) NOT NULL,          -- 冗余自 automation_assessment（便于看板查询）
  blocked_reason    varchar(512),                 -- 卡点原因（FR-1.7）
  stage_history     jsonb NOT NULL DEFAULT '[]',  -- [{stage,status,started_at,finished_at,operator,result,error}]
  credential_id     bigint,
  detection_job_id  bigint,
  quote_id          bigint,
  contract_id       bigint,
  payment_id        bigint,
  config_batch_id   bigint,
  started_at        timestamptz NOT NULL,
  finished_at       timestamptz,
  version           int NOT NULL DEFAULT 0,
  created_at        timestamptz NOT NULL,
  updated_at        timestamptz NOT NULL
);
CREATE UNIQUE INDEX uq_intake_run_no ON aap_intake_run (run_no);
CREATE INDEX idx_intake_run_stage ON aap_intake_run (current_stage, stage_status);
CREATE INDEX idx_intake_run_provider ON aap_intake_run (provider_id, started_at DESC);
```

**用途**：FR-1.7 看板的数据源；`stage_history` 支撑断点续跑（FR-1.8）与全程留痕（FR-1.9）。

---

## 13. 跨表规则增量（续接既有 C1–C12）

| 编号 | 规则 |
| --- | --- |
| C13 | `aap_supply_unit (provider_id, model_name)` 唯一；`PER_MODEL` 渠道与供给单元 1:1 |
| C14 | `aap_channel_price` 同一供给单元至多一条当前生效价；调价只增不改（历史留痕） |
| C15 | `aap_model_price` 同一模型同一角色至多一条当前生效价（`effective_to IS NULL`） |
| C16 | `aap_config_batch_item.idempotency_key` 全局唯一；dry-run 批次禁止产生网关写入 |
| C17 | `aap_quality_feedback` 唯一键 `(supply_unit_id, stat_hour, source)` 支持 UPSERT 幂等 |
| C18 | 治理动作（降权/停用）必须能在 `aap_quality_feedback`/`aap_price_drift`/`aap_automation_assessment` 中找到依据（可解释性） |

---

## 14. 迁移与回滚

| 版本 | 内容 | 回滚 |
| --- | --- | --- |
| `V15__supply_unit_and_channel_granularity.sql` | 建 `aap_supply_unit`；`aap_channel_binding` 加列与索引；**数据回填**：把既有「供应商级」渠道按 `models` 拆分出供给单元（`granularity='PER_PROVIDER'` 保留原渠道，另建 `PER_MODEL` 供给单元记录） | 回滚脚本删列、删表；既有渠道数据不动（因为新增列可空） |
| `V16__model_catalog_and_prices.sql` | `aap_model_catalog`、`aap_model_price`、`aap_channel_price` + 三个只读视图 | 删表删视图 |
| `V17__routing_quality_and_config_batch.sql` | `aap_routing_policy`、`aap_quality_feedback`、`aap_config_batch`(+`_item`) | 删表 |
| `V18__intake_run_and_guards.sql` | `aap_intake_run`、`aap_automation_assessment`、`aap_price_drift` | 删表 |

**回填策略（V15 关键）**：不迁移既有渠道（避免动生产）；只**登记**供给单元并标记
`granularity='PER_PROVIDER'`，由管理端「重配置」按需把长尾之外的模型逐批拆分为模型级渠道（DR-03 的平滑演进）。
回填脚本必须幂等，且给出「将拆分多少渠道」的 dry-run 报告（AC-10）。
