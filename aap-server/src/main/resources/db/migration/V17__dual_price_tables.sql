-- =====================================================================================
-- V17：双价格表（商品域）—— 模型对外价 + 渠道采购价
-- 真源：docs/product/02-全局ER时序与API.md §2/§4；specs/001-intake-automation/data-model.md
-- 依据：docs/product/03-开源项目调研与选型.md §5.2 —— 开源只有一张价目表，
--       「对外价 vs 采购价 + 来源可回溯到报价单/合同 + 版本化只增不改」是自研护城河（方案 A）。
--
-- 为什么必须两张表而不是一张：
--   同一模型有两个价格视角 —— 平台卖给客户多少钱（对外价）、平台从供应商采购多少钱（采购价）。
--   合成一张表会导致「调价」同时改成本与售价，毛利无法归因，历史账单也无法复算。
--   分表后：对外价只增不改（历史账单永远算得清），采购价按供给单元生效区间管理（可比价、可回溯合同）。
--
-- 幂等：if not exists；回滚见文件尾。
-- =====================================================================================

create sequence if not exists seq_model_price start 1 increment 1;
create sequence if not exists seq_channel_price start 1 increment 1;

-- -------------------------------------------------------------------------------------
-- 模型价格（平台视角）：对外价，版本化，只增不改
-- -------------------------------------------------------------------------------------
create table if not exists aap_model_price (
    id              bigint primary key,
    model_id        bigint        not null,
    price_version   integer       not null,
    currency        varchar(8)    not null default 'USD',
    base_price      numeric(18,8),
    public_price    numeric(18,8) not null,
    unit            varchar(32)   not null default 'PER_1M_TOKENS',
    effective_from  timestamptz   not null,
    effective_to    timestamptz,
    status          varchar(16)   not null default 'ACTIVE',
    source          varchar(32)   not null default 'MANUAL',
    source_ref      varchar(255),
    note            varchar(512),
    created_at      timestamptz   not null default now(),
    updated_at      timestamptz   not null default now(),
    created_by      bigint,
    updated_by      bigint,
    deleted         boolean       not null default false,
    version         integer       not null default 0
);

comment on table aap_model_price is '模型对外价（平台视角）：版本化只增不改，历史账单引用旧版本';
comment on column aap_model_price.base_price is '基准价（如上游官方价），仅用于毛利归因，不参与定价';
comment on column aap_model_price.public_price is '对外价（平台卖价），客户端可见的唯一价格';
comment on column aap_model_price.price_version is '同一模型的第 N 个价格版本；调价必须新建版本，不得原地改（否则历史账单算不出）';
comment on column aap_model_price.source is 'MANUAL/LITELLM/IMPORT：可追溯到价格来源（LiteLLM 字典仅作数据，不引运行时）';

create unique index if not exists uk_model_price_version
    on aap_model_price (model_id, price_version) where deleted = false;
create index if not exists idx_model_price_effective
    on aap_model_price (model_id, effective_from desc) where deleted = false;

-- -------------------------------------------------------------------------------------
-- 渠道价格（采购视角）：(模型 × 供应商) 的生效价，必须可回溯合同/报价单
-- -------------------------------------------------------------------------------------
create table if not exists aap_channel_price (
    id               bigint primary key,
    supply_unit_id   bigint        not null,
    provider_id      bigint        not null,
    model_id         bigint,
    price            numeric(18,8) not null,
    currency         varchar(8)    not null default 'USD',
    unit             varchar(32)   not null default 'PER_1M_TOKENS',
    effective_from   timestamptz   not null,
    effective_to     timestamptz,
    status           varchar(16)   not null default 'ACTIVE',
    source_type      varchar(16)   not null,
    quote_id         bigint,
    contract_id      bigint,
    source_ref       varchar(255),
    note             varchar(512),
    created_at       timestamptz   not null default now(),
    updated_at       timestamptz   not null default now(),
    created_by       bigint,
    updated_by       bigint,
    deleted          boolean       not null default false,
    version          integer       not null default 0
);

comment on table aap_channel_price is '渠道采购价（模型×供应商）：毛利视图的输入端，来源必须可回溯';
comment on column aap_channel_price.source_type is 'QUOTE/CONTRACT/MANUAL：优先引用合同价，报价单价仅过渡';
comment on column aap_channel_price.effective_from is '生效起点；(supply_unit_id, effective_from) 唯一，避免同一时刻两个价';
comment on column aap_channel_price.contract_id is '来源合同；比价矩阵与毛利视图据此回答「这个价从哪来的」';

create unique index if not exists uk_channel_price_from
    on aap_channel_price (supply_unit_id, effective_from) where deleted = false;
create index if not exists idx_channel_price_effective
    on aap_channel_price (supply_unit_id, effective_from desc) where deleted = false;
create index if not exists idx_channel_price_provider
    on aap_channel_price (provider_id, status) where deleted = false;

-- =====================================================================================
-- 回滚（手工）：
--   drop table if exists aap_channel_price;
--   drop table if exists aap_model_price;
--   drop sequence if exists seq_channel_price;
--   drop sequence if exists seq_model_price;
-- =====================================================================================
