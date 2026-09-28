-- =====================================================================================
-- V15：供给单元（模型 × 供应商）+ 渠道绑定粒度改造
-- 真源：specs/001-intake-automation/spec.md §3.2/§3.3（渠道粒度范式、命名规则）
--       specs/001-intake-automation/data-model.md §2/§3；plan.md M4
--
-- 据实前提（非设计假设，均为 dev 库实测结构）：
--   * aap_channel_binding 已存在：models 为 jsonb、channel_name 为 varchar(64)、
--     priority integer / weight integer 已有 —— 故本迁移**不重建**这些列；
--   * aap_model / aap_vendor 已由 V9 建立（模型目录），本迁移**不重建**；
--   * 因此 V15 只做两件事：建供给单元表 + 给绑定表补粒度列。
--
-- 幂等：if not exists（与 V2/V4–V9 既有做法一致），重跑不报错。
-- 回滚：见文件尾注释（删表删列；既有渠道数据不受影响，因新列可空）。
-- =====================================================================================

create sequence if not exists seq_supply_unit start 1 increment 1;

-- -------------------------------------------------------------------------------------
-- 供给单元：可调度单元 = 模型 × 供应商（spec §3.2）
-- -------------------------------------------------------------------------------------
create table if not exists aap_supply_unit (
    id                  bigint primary key,
    provider_id         bigint       not null,
    credential_id       bigint,
    model_name          varchar(128) not null,
    model_slug          varchar(160) not null,
    model_uid           varchar(128),
    status              varchar(32)  not null default 'PENDING',
    detect_total_score  numeric(6,2),
    detect_confidence   varchar(16),
    quality_score       numeric(6,2),
    routing_priority    integer      not null default 0,
    routing_weight      integer      not null default 0,
    auto_ban_enabled    boolean      not null default true,
    binding_id          bigint,
    granularity         varchar(16)  not null default 'PER_MODEL',
    version             integer      not null default 0,
    created_at          timestamptz  not null default now(),
    updated_at          timestamptz  not null default now(),
    created_by          bigint,
    updated_by          bigint,
    deleted             boolean      not null default false
);

comment on table aap_supply_unit is '供给单元 = 模型 × 供应商（一模型一渠道的聚合根，spec §3.2）';
comment on column aap_supply_unit.model_slug is '渠道名用的归一 slug（R-55；超长含 4 位哈希后缀）';
comment on column aap_supply_unit.model_uid is '关联 aap_model.model_uid（V9 模型目录），可空';
comment on column aap_supply_unit.status is 'PENDING/CONFIGURING/ONLINE/DEGRADED/SUSPENDED/OFFLINE';
comment on column aap_supply_unit.granularity is 'PER_MODEL 一模型一渠道 / PER_PROVIDER 合并渠道（DR-03 可配策略）';
comment on column aap_supply_unit.quality_score is '运行质量分，仅由质量反馈聚合任务写入（可解释性 R-64）';
comment on column aap_supply_unit.binding_id is '对应渠道绑定（PER_MODEL 时 1:1）';

-- 同一供应商同一模型只有一个供给单元（C13）
create unique index if not exists uk_supply_unit_provider_model
    on aap_supply_unit (provider_id, model_name) where deleted = false;
create index if not exists idx_supply_unit_model_status
    on aap_supply_unit (model_name, status) where deleted = false;
create index if not exists idx_supply_unit_provider
    on aap_supply_unit (provider_id, created_at desc, id desc) where deleted = false;

-- -------------------------------------------------------------------------------------
-- 渠道绑定：补粒度列（不重建既有列）
-- -------------------------------------------------------------------------------------
alter table aap_channel_binding add column if not exists supply_unit_id bigint;
alter table aap_channel_binding add column if not exists model_name varchar(128);
alter table aap_channel_binding add column if not exists granularity varchar(16) not null default 'PER_MODEL';

comment on column aap_channel_binding.supply_unit_id is '所属供给单元（PER_MODEL 时唯一）';
comment on column aap_channel_binding.model_name is '该渠道唯一模型（PER_MODEL）；合并模式下为 null';
comment on column aap_channel_binding.granularity is 'PER_MODEL / PER_PROVIDER —— 命名与校验据此分流（R-54/R-56）';

-- 同一供给单元只能有一条 PER_MODEL 渠道
create unique index if not exists uk_binding_supply_unit
    on aap_channel_binding (supply_unit_id)
    where deleted = false and granularity = 'PER_MODEL' and supply_unit_id is not null;

create index if not exists idx_binding_model
    on aap_channel_binding (model_name, status) where deleted = false;

-- =====================================================================================
-- 回滚（手工执行，Flyway 不自动回滚）：
--   drop index if exists uk_binding_supply_unit;
--   drop index if exists idx_binding_model;
--   alter table aap_channel_binding drop column if exists supply_unit_id;
--   alter table aap_channel_binding drop column if exists model_name;
--   alter table aap_channel_binding drop column if exists granularity;
--   drop table if exists aap_supply_unit;
--   drop sequence if exists seq_supply_unit;
-- 既有渠道/模型/厂商数据不受影响（新列可空、新表独立）。
-- =====================================================================================
