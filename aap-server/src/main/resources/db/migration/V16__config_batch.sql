-- =====================================================================================
-- V16：批量配置批次（配置编排的可观测载体）
-- 真源：specs/001-intake-automation/spec.md §4 FR-2.5/FR-6.2、data-model.md §9；plan.md §3.2
--
-- 为什么需要这张表：编排器一次要处理 N 个供给单元（M 供应商 × N 模型后数量级放大），
-- 每个单元的执行结果必须**独立可查、可单独重试/回滚**（R-59 单模型隔离）——
-- 没有批次与明细，失败就只能整批重来，与「细粒度调度」的收益相抵。
-- dry-run 的差异清单也落在这里（diff_payload），作为「预演不写生产」的证据（AC-10）。
--
-- 幂等：if not exists（与 V2/V4–V9/V15 既有做法一致）。
-- 回滚：见文件尾注释。
-- =====================================================================================

create sequence if not exists seq_config_batch start 1 increment 1;
create sequence if not exists seq_config_batch_item start 1 increment 1;

-- -------------------------------------------------------------------------------------
-- 批次主表
-- -------------------------------------------------------------------------------------
create table if not exists aap_config_batch (
    id                  bigint primary key,
    batch_no            varchar(64)  not null,
    batch_type          varchar(24)  not null,
    mode                varchar(16)  not null,
    trigger_source      varchar(24)  not null,
    status              varchar(24)  not null,
    total_count         integer      not null default 0,
    succeeded_count     integer      not null default 0,
    failed_count        integer      not null default 0,
    mismatch_count      integer      not null default 0,
    rate_limit_per_sec  integer      not null default 5,
    diff_payload        jsonb,
    operator_id         bigint,
    started_at          timestamptz,
    finished_at         timestamptz,
    created_at          timestamptz  not null default now(),
    updated_at          timestamptz  not null default now(),
    created_by          bigint,
    updated_by          bigint,
    deleted             boolean      not null default false,
    version             integer      not null default 0
);

comment on table aap_config_batch is '批量配置批次（CFG-B{yyyyMM}-{seq}）：编排器五步的执行记录与 dry-run 差异清单';
comment on column aap_config_batch.batch_type is 'ADD_CHANNEL/UPDATE_CHANNEL/WRITE_PRICE/RECONFIG/OFFLINE/ENABLE/DISABLE';
comment on column aap_config_batch.mode is 'DRY_RUN（只出差异清单、零写入）/ APPLY';
comment on column aap_config_batch.trigger_source is 'INTAKE_AUTO/ADMIN_MANUAL/POLICY_CHANGE/CREDENTIAL_UPDATE';
comment on column aap_config_batch.rate_limit_per_sec is '限速（R-57：默认 5，上限 5）';
comment on column aap_config_batch.diff_payload is 'dry-run 产出的差异清单（AC-10 零写入的证据）';
comment on column aap_config_batch.mismatch_count is '回读不一致数（R-58：不一致必须可见，不得静默成功）';

create unique index if not exists uk_config_batch_no
    on aap_config_batch (batch_no) where deleted = false;
create index if not exists idx_config_batch_status
    on aap_config_batch (status, created_at desc, id desc) where deleted = false;

-- -------------------------------------------------------------------------------------
-- 批次明细（逐供给单元）；幂等键全局唯一（C-11 沿用的幂等纪律）
-- -------------------------------------------------------------------------------------
create table if not exists aap_config_batch_item (
    id                bigint primary key,
    batch_id          bigint       not null,
    supply_unit_id    bigint,
    provider_id       bigint,
    model_name        varchar(128),
    action            varchar(24)  not null,
    status            varchar(24)  not null,
    reason            varchar(512),
    idempotency_key   varchar(128),
    request_summary   jsonb,
    response_summary  jsonb,
    readback_equal    boolean,
    readback_diff     jsonb,
    attempt_count     integer      not null default 0,
    last_error        varchar(512),
    created_at        timestamptz  not null default now(),
    updated_at        timestamptz  not null default now(),
    deleted           boolean      not null default false,
    version           integer      not null default 0
);

comment on table aap_config_batch_item is '批次明细：每个供给单元一行（R-59 单模型隔离，可单独重试/回滚）';
comment on column aap_config_batch_item.action is 'CREATE/UPDATE/SKIP/DISABLE';
comment on column aap_config_batch_item.status is 'PENDING/RUNNING/SUCCEEDED/FAILED/MISMATCH/ROLLED_BACK';
comment on column aap_config_batch_item.request_summary is '请求摘要（**必须脱敏**：key 一律以 mask 表示，C-03）';
comment on column aap_config_batch_item.readback_equal is '写后回读是否与期望一致（R-58）';

create unique index if not exists uk_config_batch_item_idem
    on aap_config_batch_item (idempotency_key) where idempotency_key is not null and deleted = false;
create index if not exists idx_config_batch_item_batch
    on aap_config_batch_item (batch_id, status) where deleted = false;

-- =====================================================================================
-- 回滚（手工执行）：
--   drop table if exists aap_config_batch_item;
--   drop table if exists aap_config_batch;
--   drop sequence if exists seq_config_batch_item;
--   drop sequence if exists seq_config_batch;
-- =====================================================================================
