-- =====================================================================================
-- AAP 服务端基线建表（V1）
--
-- 真源：docs/backend/01-ER数据模型.md（54 张表）· .calicat/prd/15-数据模型ER与数据字典.md
-- 约定（doc 01 §1）：主键 bigint 雪花（应用生成，非自增）· 逻辑外键（不建 DB FK）
--   · 时间 timestamptz UTC · 软删除 deleted boolean · 乐观锁 version int
--   · 金额 numeric(18,6) · 半结构化 jsonb · 枚举 varchar(32)
--   · 审计字段 id/created_at/updated_at/created_by/updated_by/deleted/version
--   · 业务唯一索引一律带 where deleted = false
--
-- 幂等：全部 create ... if not exists / create index if not exists —— 重跑不报错（dev SKILL §7 治本原则）
-- =====================================================================================

-- ---------------------------------------------------------------- iam
create table if not exists aap_provider_account (
    id              bigint primary key,
    phone_cipher    text,
    phone_hash      char(64),
    phone_masked    varchar(16),
    nickname        varchar(64),
    wx_openid       varchar(64),
    wx_unionid      varchar(64),
    role            varchar(32) not null default 'SUPPLIER',
    status          varchar(32) not null default 'ACTIVE',
    sms_2fa         boolean not null default false,
    wechat_subscribed boolean not null default false,
    last_login_at   timestamptz,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    created_by      bigint,
    updated_by      bigint,
    deleted         boolean not null default false,
    version         int not null default 0
);
create unique index if not exists uq_account_phone_hash on aap_provider_account (phone_hash) where deleted = false;
create unique index if not exists uq_account_wx_openid on aap_provider_account (wx_openid) where deleted = false and wx_openid is not null;
create index if not exists idx_account_wx_unionid on aap_provider_account (wx_unionid);

create table if not exists aap_admin_user (
    id              bigint primary key,
    username        varchar(64) not null,
    password_hash   varchar(128) not null,
    display_name    varchar(64),
    role            varchar(32) not null,
    status          varchar(32) not null default 'ACTIVE',
    phone_masked    varchar(16),
    last_login_at   timestamptz,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    created_by      bigint,
    updated_by      bigint,
    deleted         boolean not null default false,
    version         int not null default 0
);
create unique index if not exists uq_admin_username on aap_admin_user (username) where deleted = false;

create table if not exists aap_role (
    id              bigint primary key,
    code            varchar(32) not null,
    name            varchar(64) not null,
    scope           varchar(16) not null default 'PROVIDER',
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create unique index if not exists uq_role_code on aap_role (code) where deleted = false;

create table if not exists aap_user_role (
    id              bigint primary key,
    user_id         bigint not null,
    user_type       varchar(16) not null default 'PROVIDER',
    role_code       varchar(32) not null,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create unique index if not exists uq_user_role on aap_user_role (user_id, user_type, role_code) where deleted = false;

create table if not exists aap_sms_code (
    id              bigint primary key,
    phone_hash      char(64) not null,
    phone_masked    varchar(16),
    scene           varchar(32) not null default 'LOGIN',
    code_hash       char(64) not null,
    sent_at         timestamptz not null default now(),
    expire_at       timestamptz not null,
    attempt_count   int not null default 0,
    locked_until    timestamptz,
    used_at         timestamptz,
    client_ip       varchar(64),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create index if not exists idx_sms_phone_sent on aap_sms_code (phone_hash, sent_at desc);

create table if not exists aap_wechat_binding (
    id              bigint primary key,
    account_id      bigint not null,
    openid          varchar(64) not null,
    unionid         varchar(64),
    bound_at        timestamptz not null default now(),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create unique index if not exists uq_wechat_openid on aap_wechat_binding (openid) where deleted = false;

create table if not exists aap_auth_token (
    id                  bigint primary key,
    account_id          bigint not null,
    subject_type        varchar(16) not null default 'PROVIDER',
    jti                 varchar(64) not null,
    refresh_token_hash  char(64),
    expire_at           timestamptz not null,
    revoked_at          timestamptz,
    user_agent          varchar(255),
    client_ip           varchar(64),
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    deleted             boolean not null default false,
    version             int not null default 0
);
create unique index if not exists uq_auth_jti on aap_auth_token (jti);
create index if not exists idx_auth_account on aap_auth_token (account_id, expire_at desc);

-- ---------------------------------------------------------------- provider
create table if not exists aap_provider (
    id                      bigint primary key,
    provider_no             varchar(32),
    provider_code           varchar(32),
    account_id              bigint,
    short_name              varchar(64),
    short_code              varchar(64),
    company_name            varchar(128),
    uscc                    varchar(18),
    industry_category       varchar(32),
    province                varchar(32),
    city                    varchar(32),
    address                 varchar(255),
    website                 varchar(255),
    contact_name            varchar(64),
    contact_title           varchar(64),
    contact_phone_cipher    text,
    contact_phone_hash      char(64),
    contact_phone_mask      varchar(16),
    contact_email           varchar(128),
    company_intro           text,
    completeness            smallint not null default 0,
    status                  varchar(32) not null default 'PENDING_CREDENTIAL',
    recheck_interval_days   int not null default 30,
    manual_override         boolean not null default false,
    override_reason         text,
    operator_tags           jsonb,
    last_detection_job_id   bigint,
    published_at            timestamptz,
    suspended_at            timestamptz,
    suspend_reason          text,
    created_at              timestamptz not null default now(),
    updated_at              timestamptz not null default now(),
    created_by              bigint,
    updated_by              bigint,
    deleted                 boolean not null default false,
    version                 int not null default 0
);
create unique index if not exists uq_provider_no on aap_provider (provider_no) where deleted = false;
create unique index if not exists uq_provider_code on aap_provider (provider_code) where deleted = false;
create unique index if not exists uq_provider_uscc on aap_provider (uscc) where deleted = false and uscc is not null;
create unique index if not exists uq_provider_short_code on aap_provider (short_code) where deleted = false and short_code is not null;
create index if not exists idx_provider_status_created on aap_provider (status, created_at desc, id desc);
create index if not exists idx_provider_account on aap_provider (account_id);

create table if not exists aap_provider_qualification (
    id              bigint primary key,
    provider_id     bigint not null,
    category        varchar(32) not null,
    file_id         bigint,
    file_name       varchar(255) not null,
    file_size       bigint,
    content_type    varchar(128),
    status          varchar(32) not null default 'UPLOADED',
    uploaded_at     timestamptz not null default now(),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    created_by      bigint,
    updated_by      bigint,
    deleted         boolean not null default false,
    version         int not null default 0
);
create index if not exists idx_qual_provider_created on aap_provider_qualification (provider_id, created_at desc, id desc);

-- ---------------------------------------------------------------- credential
create table if not exists aap_credential (
    id                          bigint primary key,
    provider_id                 bigint not null,
    alias                       varchar(64),
    primary_flag                boolean not null default false,
    base_url                    varchar(255) not null,
    api_key_cipher              text not null,
    api_key_mask                varchar(32) not null,
    api_key_fingerprint         char(64) not null,
    declared_vendor             varchar(64),
    declared_rpm                int,
    declared_tpm                int,
    declared_context_window     int,
    model_list                  jsonb,
    env_tag                     varchar(32),
    status                      varchar(32) not null default 'PENDING_PRECHECK',
    detection_status            varchar(32) not null default 'PENDING',
    latest_report_id            bigint,
    precheck_passed             boolean not null default false,
    precheck_at                 timestamptz,
    last_used_at                timestamptz,
    created_at                  timestamptz not null default now(),
    updated_at                  timestamptz not null default now(),
    created_by                  bigint,
    updated_by                  bigint,
    deleted                     boolean not null default false,
    version                     int not null default 0
);
-- C1：同供应商至多 1 条主凭证
create unique index if not exists uq_credential_primary on aap_credential (provider_id) where primary_flag = true and deleted = false;
-- AC-09：同供应商下 api_key 指纹唯一
create unique index if not exists uq_credential_fingerprint on aap_credential (provider_id, api_key_fingerprint) where deleted = false;
create index if not exists idx_credential_provider_created on aap_credential (provider_id, created_at desc, id desc);
create index if not exists idx_credential_status on aap_credential (detection_status);

create table if not exists aap_credential_precheck (
    id              bigint primary key,
    credential_id   bigint not null,
    status          varchar(16) not null,
    connectivity_ok boolean not null default false,
    auth_ok         boolean not null default false,
    models_ok       boolean not null default false,
    error_code      varchar(16),
    error_msg       varchar(255),
    latency_ms      int,
    checked_at      timestamptz not null default now(),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create index if not exists idx_precheck_credential_checked on aap_credential_precheck (credential_id, checked_at desc, id desc);

create table if not exists aap_provider_challenge (
    id              bigint primary key,
    provider_id     bigint not null,
    credential_id   bigint,
    challenge_code  varchar(64) not null,
    signature       varchar(128),
    verified_at     timestamptz,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create unique index if not exists uq_challenge_code on aap_provider_challenge (challenge_code);

-- ---------------------------------------------------------------- detection
create table if not exists aap_detection_config (
    id              bigint primary key,
    version_no      varchar(32) not null,
    name            varchar(64) not null,
    pass_score      int not null default 70,
    veto_rule       jsonb,
    status          varchar(32) not null default 'DRAFT',
    published_at    timestamptz,
    published_by    bigint,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    created_by      bigint,
    updated_by      bigint,
    deleted         boolean not null default false,
    version         int not null default 0
);
create unique index if not exists uq_detection_config_version on aap_detection_config (version_no) where deleted = false;
create index if not exists idx_detection_config_status on aap_detection_config (status, created_at desc, id desc);

create table if not exists aap_detection_config_probe (
    id              bigint primary key,
    config_id       bigint not null,
    probe_code      varchar(8) not null,
    probe_name      varchar(64) not null,
    enabled         boolean not null default true,
    weight          numeric(6,4) not null default 0,
    timeout_seconds int not null default 180,
    params          jsonb,
    seq             int not null default 0,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create unique index if not exists uq_config_probe on aap_detection_config_probe (config_id, probe_code) where deleted = false;

create table if not exists aap_detection_job (
    id                  bigint primary key,
    job_no              varchar(32) not null,
    provider_id         bigint not null,
    credential_id       bigint not null,
    trigger_type        varchar(16) not null default 'FIRST',
    status              varchar(32) not null default 'QUEUED',
    active_flag         boolean not null default true,
    config_id           bigint,
    config_snapshot     jsonb,
    started_at          timestamptz,
    finished_at         timestamptz,
    total_score         numeric(5,2),
    result              varchar(16),
    confidence          varchar(16),
    cost_estimate_usd   numeric(18,6),
    cost_actual_usd     numeric(18,6),
    challenge_verified  boolean not null default false,
    error_code          varchar(16),
    error_msg           varchar(500),
    attempt_count       int not null default 0,
    progress_percent    numeric(5,2),
    progress_finished   int,
    progress_total      int,
    eta_minutes         numeric(6,2),
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    created_by          bigint,
    updated_by          bigint,
    deleted             boolean not null default false,
    version             int not null default 0
);
create unique index if not exists uq_job_no on aap_detection_job (job_no);
-- C2：同凭证同时至多 1 个活跃检测任务（E-1301 的数据库兜底）
create unique index if not exists uq_job_active on aap_detection_job (credential_id) where active_flag = true and deleted = false;
create index if not exists idx_job_status_created on aap_detection_job (status, created_at, id);
create index if not exists idx_job_provider_created on aap_detection_job (provider_id, created_at desc, id desc);

create table if not exists aap_detection_result (
    id              bigint primary key,
    job_id          bigint not null,
    probe_code      varchar(8) not null,
    probe_name      varchar(64),
    status          varchar(32) not null,
    score           numeric(5,2),
    weight_original numeric(6,4),
    weight_used     numeric(6,4),
    metrics         jsonb,
    evidence        text,
    evidence_url    varchar(500),
    explanation     text,
    attempt_count   int not null default 0,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create unique index if not exists uq_result_job_probe on aap_detection_result (job_id, probe_code) where deleted = false;

create table if not exists aap_detection_baseline (
    id              bigint primary key,
    model_name      varchar(128) not null,
    vendor          varchar(64),
    tokenizer_probe jsonb,
    behavior_vector jsonb,
    context_max     int,
    source          varchar(64),
    baseline_version varchar(32),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create index if not exists idx_baseline_model on aap_detection_baseline (model_name, vendor);

create table if not exists aap_baseline_sample (
    id              bigint primary key,
    baseline_id     bigint not null,
    sample_type     varchar(32) not null,
    payload         jsonb,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create index if not exists idx_baseline_sample on aap_baseline_sample (baseline_id, sample_type);

create table if not exists aap_probe_question (
    id              bigint primary key,
    difficulty      varchar(16) not null default 'MEDIUM',
    prompt          text not null,
    expected_type   varchar(32),
    weight          numeric(6,4) not null default 1,
    enabled         boolean not null default true,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);

-- ---------------------------------------------------------------- report
create table if not exists aap_report_template (
    id              bigint primary key,
    template_no     varchar(32) not null,
    version_no      varchar(32) not null,
    title           varchar(128) not null,
    logo_file_id    bigint,
    section_order   jsonb,
    disclaimer      text,
    status          varchar(32) not null default 'DRAFT',
    published_at    timestamptz,
    published_by    bigint,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    created_by      bigint,
    updated_by      bigint,
    deleted         boolean not null default false,
    version         int not null default 0
);
create unique index if not exists uq_report_template_ver on aap_report_template (template_no, version_no) where deleted = false;
create index if not exists idx_report_template_status on aap_report_template (status, created_at desc, id desc);

create table if not exists aap_report (
    id                  bigint primary key,
    report_no           varchar(32) not null,
    job_id              bigint not null,
    provider_id         bigint not null,
    credential_id       bigint,
    template_id         bigint,
    template_snapshot   jsonb,
    total_score         numeric(5,2),
    result              varchar(16),
    confidence          varchar(16),
    veto_triggered      boolean not null default false,
    verdict             text,
    provider_name       varchar(128),
    provider_code       varchar(32),
    channel_name        varchar(64),
    api_key_masked      varchar(32),
    model_list          jsonb,
    detected_at         timestamptz,
    duration_seconds    int,
    cost_estimate_usd   numeric(18,6),
    cost_actual_usd     numeric(18,6),
    rendered_html       text,
    pdf_file_id         bigint,
    disclaimer          text,
    status              varchar(16) not null default 'GENERATED',
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    created_by          bigint,
    updated_by          bigint,
    deleted             boolean not null default false,
    version             int not null default 0
);
create unique index if not exists uq_report_no on aap_report (report_no) where deleted = false;
create unique index if not exists uq_report_job on aap_report (job_id) where deleted = false;
create index if not exists idx_report_provider_created on aap_report (provider_id, created_at desc, id desc);

create table if not exists aap_report_section (
    id              bigint primary key,
    report_id       bigint not null,
    section_code    varchar(8) not null,
    section_name    varchar(64) not null,
    avg_score       numeric(5,2),
    scored          boolean not null default false,
    note            text,
    items           jsonb,
    seq             int not null default 0,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create unique index if not exists uq_report_section on aap_report_section (report_id, section_code) where deleted = false;

-- ---------------------------------------------------------------- quote
create table if not exists aap_quote (
    id                      bigint primary key,
    quote_no                varchar(32) not null,
    provider_id             bigint not null,
    credential_id           bigint,
    name                    varchar(64),
    status                  varchar(32) not null default 'DRAFT',
    current_version         int not null default 1,
    currency                varchar(8) not null default 'USD',
    valid_from              timestamptz,
    valid_to                timestamptz,
    item_count              int not null default 0,
    remark                  text,
    reject_reason_code      varchar(32),
    reject_reason_text      text,
    submitted_at            timestamptz,
    submitted_by            bigint,
    withdrawn_at            timestamptz,
    reviewed_by             bigint,
    reviewed_at             timestamptz,
    approved_quote_version  int,
    contract_id             bigint,
    last_compilation_id     bigint,
    source_hash             char(64),
    created_at              timestamptz not null default now(),
    updated_at              timestamptz not null default now(),
    created_by              bigint,
    updated_by              bigint,
    deleted                 boolean not null default false,
    version                 int not null default 0
);
create unique index if not exists uq_quote_no on aap_quote (quote_no);
create index if not exists idx_quote_provider_created on aap_quote (provider_id, created_at desc, id desc);
create index if not exists idx_quote_status_created on aap_quote (status, created_at desc, id desc);

create table if not exists aap_quote_version (
    id              bigint primary key,
    quote_id        bigint not null,
    version_no      int not null,
    snapshot        jsonb not null,
    source_hash     char(64),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    created_by      bigint,
    updated_by      bigint,
    deleted         boolean not null default false,
    version         int not null default 0
);
create unique index if not exists uq_quote_version on aap_quote_version (quote_id, version_no) where deleted = false;

create table if not exists aap_quote_item (
    id                      bigint primary key,
    quote_id                bigint not null,
    model_name              varchar(128) not null,
    model_alias             varchar(64),
    input_price             numeric(18,6),
    output_price            numeric(18,6),
    cache_read_price        numeric(18,6),
    cache_write_price       numeric(18,6),
    cache_write_1h_price    numeric(18,6),
    image_input_price       numeric(18,6),
    audio_input_price       numeric(18,6),
    image_output_price      numeric(18,6),
    audio_output_price      numeric(18,6),
    tier_label              varchar(64),
    billing_mode            varchar(32),
    compile_status          varchar(32) not null default 'NOT_COMPILED',
    note                    text,
    created_at              timestamptz not null default now(),
    updated_at              timestamptz not null default now(),
    created_by              bigint,
    updated_by              bigint,
    deleted                 boolean not null default false,
    version                 int not null default 0
);
-- C3：同报价单内模型不重复
create unique index if not exists uq_quote_item_model on aap_quote_item (quote_id, model_name) where deleted = false;
create index if not exists idx_quote_item_quote on aap_quote_item (quote_id, created_at desc, id desc);

create table if not exists aap_price_time_rule (
    id                  bigint primary key,
    item_id             bigint not null,
    tz                  varchar(64) not null default 'Asia/Shanghai',
    weekday_scope       varchar(16) not null default 'ALL',
    peak_multiplier     numeric(12,6),
    offpeak_multiplier  numeric(12,6),
    peak_price_override numeric(18,6),
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    deleted             boolean not null default false,
    version             int not null default 0
);
-- C4：每明细行至多 1 条时段规则
create unique index if not exists uq_time_rule_item on aap_price_time_rule (item_id) where deleted = false;

create table if not exists aap_price_time_segment (
    id              bigint primary key,
    time_rule_id    bigint not null,
    start_time      time not null,
    end_time        time not null,
    seq             int not null default 0,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create index if not exists idx_time_segment_rule on aap_price_time_segment (time_rule_id, seq);

create table if not exists aap_price_tier_rule (
    id              bigint primary key,
    item_id         bigint not null,
    tier_field      varchar(16) not null default 'len',
    price_strategy  varchar(16) not null default 'OVERRIDE',
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
-- C4：每明细行至多 1 条阶梯规则
create unique index if not exists uq_tier_rule_item on aap_price_tier_rule (item_id) where deleted = false;

create table if not exists aap_price_tier (
    id                  bigint primary key,
    tier_rule_id        bigint not null,
    seq                 int not null,
    min_value           numeric(18,6),
    max_value           numeric(18,6),
    label               varchar(64),
    input_price         numeric(18,6),
    output_price        numeric(18,6),
    cache_read_price    numeric(18,6),
    multiplier          numeric(12,6),
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    deleted             boolean not null default false,
    version             int not null default 0
);
create unique index if not exists uq_price_tier_seq on aap_price_tier (tier_rule_id, seq) where deleted = false;

create table if not exists aap_price_request_rule (
    id              bigint primary key,
    item_id         bigint not null,
    when_expr       varchar(255) not null,
    multiplier      numeric(12,6) not null,
    enabled         boolean not null default true,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create index if not exists idx_request_rule_item on aap_price_request_rule (item_id);

create table if not exists aap_reference_price (
    id              bigint primary key,
    model_name      varchar(128) not null,
    vendor          varchar(64),
    input_price     numeric(18,6),
    output_price    numeric(18,6),
    effective_from  timestamptz,
    effective_to    timestamptz,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create index if not exists idx_reference_price_model on aap_reference_price (model_name, vendor);

-- ---------------------------------------------------------------- review
create table if not exists aap_review_task (
    id                      bigint primary key,
    quote_id                bigint not null,
    provider_id             bigint,
    status                  varchar(32) not null default 'PENDING',
    claimed_by              bigint,
    claimed_at              timestamptz,
    tech_reviewed_by        bigint,
    tech_reviewed_at        timestamptz,
    tech_metrics_snapshot   jsonb,
    review_comment          text,
    reject_reason_code      varchar(32),
    reject_reason_text      text,
    created_at              timestamptz not null default now(),
    updated_at              timestamptz not null default now(),
    created_by              bigint,
    updated_by              bigint,
    deleted                 boolean not null default false,
    version                 int not null default 0
);
create unique index if not exists uq_review_quote on aap_review_task (quote_id) where deleted = false;
create index if not exists idx_review_status_created on aap_review_task (status, created_at desc, id desc);

create table if not exists aap_review_record (
    id              bigint primary key,
    quote_id        bigint not null,
    task_id         bigint,
    action          varchar(32) not null,
    operator_id     bigint,
    operator_name   varchar(64),
    before_status   varchar(32),
    after_status    varchar(32),
    comment         text,
    snapshot        jsonb,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create index if not exists idx_review_record_quote on aap_review_record (quote_id, created_at desc, id desc);

-- ---------------------------------------------------------------- contract
create table if not exists aap_contract (
    id                      bigint primary key,
    contract_no             varchar(32) not null,
    quote_id                bigint,
    provider_id             bigint not null,
    title                   varchar(128),
    status                  varchar(32) not null default 'CREATED',
    sign_channel            varchar(16) not null default 'OFFLINE',
    cooperation_mode        varchar(32),
    valid_from              timestamptz,
    valid_to                timestamptz,
    settlement_cycle        varchar(32),
    platform_fee_rate       numeric(6,4),
    currency                varchar(8) not null default 'USD',
    min_settlement_amount   numeric(18,6),
    sign_deadline           timestamptz,
    signer_name             varchar(64),
    signer_phone_mask       varchar(16),
    sign_method             varchar(16),
    terms                   jsonb,
    file_id                 bigint,
    signed_at               timestamptz,
    archived_at             timestamptz,
    voided_reason           text,
    created_at              timestamptz not null default now(),
    updated_at              timestamptz not null default now(),
    created_by              bigint,
    updated_by              bigint,
    deleted                 boolean not null default false,
    version                 int not null default 0
);
create unique index if not exists uq_contract_no on aap_contract (contract_no) where deleted = false;
create index if not exists idx_contract_provider_created on aap_contract (provider_id, created_at desc, id desc);
create index if not exists idx_contract_status_created on aap_contract (status, created_at desc, id desc);

create table if not exists aap_contract_sign (
    id              bigint primary key,
    contract_id     bigint not null,
    signer_type     varchar(16) not null,
    signer_name     varchar(64),
    sign_method     varchar(16),
    sms_code_id     bigint,
    tone            varchar(16),
    signed_at       timestamptz not null default now(),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create index if not exists idx_contract_sign_contract on aap_contract_sign (contract_id, signed_at);

-- ---------------------------------------------------------------- settlement
create table if not exists aap_payment_record (
    id              bigint primary key,
    provider_id     bigint not null,
    contract_id     bigint,
    statement_id    bigint,
    amount          numeric(18,6) not null,
    currency        varchar(8) not null default 'USD',
    status          varchar(32) not null default 'UNSETTLED',
    voucher_file_id bigint,
    paid_at         timestamptz,
    confirmed_by    bigint,
    confirmed_at    timestamptz,
    remark          text,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    created_by      bigint,
    updated_by      bigint,
    deleted         boolean not null default false,
    version         int not null default 0
);
create index if not exists idx_payment_provider_created on aap_payment_record (provider_id, created_at desc, id desc);
create index if not exists idx_payment_status_created on aap_payment_record (status, created_at desc, id desc);

create table if not exists aap_settlement_statement (
    id              bigint primary key,
    statement_no    varchar(32) not null,
    provider_id     bigint not null,
    period_from     timestamptz,
    period_to       timestamptz,
    total_amount    numeric(18,6) not null default 0,
    platform_fee    numeric(18,6) not null default 0,
    status          varchar(32) not null default 'DRAFT',
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    created_by      bigint,
    updated_by      bigint,
    deleted         boolean not null default false,
    version         int not null default 0
);
create unique index if not exists uq_statement_no on aap_settlement_statement (statement_no) where deleted = false;

create table if not exists aap_settlement_line (
    id              bigint primary key,
    statement_id    bigint not null,
    channel_id      bigint,
    model_name      varchar(128),
    total_tokens    bigint not null default 0,
    quota_raw       numeric(18,6) not null default 0,
    amount          numeric(18,6) not null default 0,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create index if not exists idx_settlement_line_statement on aap_settlement_line (statement_id);

-- ---------------------------------------------------------------- compilation
create table if not exists aap_compiled_expression (
    id                  bigint primary key,
    quote_id            bigint not null,
    quote_version       int not null,
    provider_id         bigint,
    status              varchar(32) not null default 'DRAFT',
    gate_status         varchar(32) not null default 'COMPILED',
    source_hash         char(64) not null,
    compiler_version    varchar(16) not null default 'v1',
    previous_expr       jsonb,
    publish_blocked     boolean not null default true,
    verify_report       jsonb,
    confirmed_by        bigint,
    confirmed_at        timestamptz,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    created_by          bigint,
    updated_by          bigint,
    deleted             boolean not null default false,
    version             int not null default 0
);
-- R-34：source_hash 幂等（同报价单同版本同 hash 不重复编译）
create unique index if not exists uq_compilation_source_hash on aap_compiled_expression (source_hash) where deleted = false;
create index if not exists idx_compilation_quote on aap_compiled_expression (quote_id, quote_version desc);
create index if not exists idx_compilation_status_created on aap_compiled_expression (status, created_at desc, id desc);

create table if not exists aap_model_expression (
    id              bigint primary key,
    compilation_id  bigint not null,
    model_name      varchar(128) not null,
    expr_version    varchar(16) not null default 'v1',
    expr            text not null,
    tier_labels     jsonb,
    rule_hits       jsonb,
    verified        boolean not null default false,
    source_hash     char(64),
    inline_expanded text,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create unique index if not exists uq_model_expression on aap_model_expression (compilation_id, model_name) where deleted = false;

create table if not exists aap_verify_run (
    id              bigint primary key,
    compilation_id  bigint not null,
    status          varchar(16) not null,
    case_total      int not null default 0,
    case_passed     int not null default 0,
    failed_field    varchar(128),
    started_at      timestamptz,
    finished_at     timestamptz,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create index if not exists idx_verify_run_compilation on aap_verify_run (compilation_id, created_at desc);

create table if not exists aap_verify_case (
    id              bigint primary key,
    run_id          bigint not null,
    case_code       varchar(16) not null,
    case_name       varchar(128),
    input           jsonb,
    expected        numeric(18,8),
    actual          numeric(18,8),
    passed          boolean not null default false,
    diff_note       varchar(255),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create index if not exists idx_verify_case_run on aap_verify_case (run_id, case_code);

-- ---------------------------------------------------------------- sync
create table if not exists aap_newapi_endpoint (
    id              bigint primary key,
    name            varchar(64) not null,
    base_url        varchar(255) not null,
    api_key_cipher  text,
    db_url_cipher   text,
    readonly        boolean not null default true,
    status          varchar(32) not null default 'ACTIVE',
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);

create table if not exists aap_channel_binding (
    id                      bigint primary key,
    provider_id             bigint not null,
    credential_id           bigint,
    endpoint_id             bigint,
    channel_id              bigint,
    channel_name            varchar(64) not null,
    tag                     varchar(64),
    group_name              varchar(64),
    priority                int not null default 0,
    weight                  int not null default 1,
    models                  jsonb,
    status                  varchar(32) not null default 'NOT_SYNCED',
    last_synced_at          timestamptz,
    last_readback_hash      char(64),
    online_channel_snapshot jsonb,
    created_at              timestamptz not null default now(),
    updated_at              timestamptz not null default now(),
    created_by              bigint,
    updated_by              bigint,
    deleted                 boolean not null default false,
    version                 int not null default 0
);
create unique index if not exists uq_channel_name on aap_channel_binding (channel_name) where deleted = false;
create index if not exists idx_binding_provider on aap_channel_binding (provider_id, created_at desc, id desc);

create table if not exists aap_sync_task (
    id                  bigint primary key,
    task_no             varchar(32) not null,
    binding_id          bigint,
    provider_id         bigint,
    compilation_id      bigint,
    task_type           varchar(32) not null,
    status              varchar(32) not null default 'PENDING',
    payload             jsonb,
    idempotency_key     varchar(128) not null,
    attempt_count       int not null default 0,
    next_retry_at       timestamptz,
    last_error          varchar(500),
    readback_equal      boolean,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    created_by          bigint,
    updated_by          bigint,
    deleted             boolean not null default false,
    version             int not null default 0
);
create unique index if not exists uq_sync_task_no on aap_sync_task (task_no) where deleted = false;
-- C11：幂等键全局唯一
create unique index if not exists uq_sync_idempotency on aap_sync_task (idempotency_key);
create index if not exists idx_sync_task_status_retry on aap_sync_task (status, next_retry_at, id);

create table if not exists aap_sync_operation (
    id                  bigint primary key,
    task_id             bigint not null,
    operation           varchar(32) not null,
    request_payload     jsonb,
    response_payload    jsonb,
    result              varchar(16),
    readback_equal      boolean,
    attempt_no          int not null default 1,
    error               varchar(500),
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    deleted             boolean not null default false,
    version             int not null default 0
);
create index if not exists idx_sync_operation_task on aap_sync_operation (task_id, created_at desc);

create table if not exists aap_sync_log (
    id                  bigint primary key,
    provider_id         bigint,
    channel_id          bigint,
    operation           varchar(32),
    idempotency_key     varchar(128),
    request_payload     jsonb,
    response_payload    jsonb,
    result              varchar(16),
    readback_equal      boolean,
    attempt_no          int,
    error               varchar(500),
    operator_id         bigint,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    deleted             boolean not null default false,
    version             int not null default 0
);
create index if not exists idx_sync_log_provider_created on aap_sync_log (provider_id, created_at desc, id desc);

-- ---------------------------------------------------------------- usage
-- 事实表：按月 RANGE 分区（15-数据模型 §7）。default 分区保证「未建月分区」时仍可写入，不丢数据。
create table if not exists aap_usage_hourly (
    id                      bigint not null,
    stat_hour               timestamptz not null,
    channel_id              bigint,
    channel_name            varchar(64),
    provider_id             bigint,
    model_name              varchar(128) not null default '',
    group_name              varchar(64) not null default '',
    request_count           bigint not null default 0,
    prompt_tokens           bigint not null default 0,
    completion_tokens       bigint not null default 0,
    total_tokens            bigint not null default 0,
    cache_read_tokens       bigint not null default 0,
    cache_write_tokens      bigint not null default 0,
    cache_write_1h_tokens   bigint not null default 0,
    image_input_tokens      bigint not null default 0,
    audio_input_tokens      bigint not null default 0,
    video_input_tokens      bigint not null default 0,
    quota_raw               numeric(18,6) not null default 0,
    cost_usd                numeric(18,6) not null default 0,
    tier_distribution       jsonb,
    cache_parse_status      varchar(32) not null default 'OK',
    source                  varchar(16) not null default 'LOG_DB',
    batch_id                bigint,
    collected_at            timestamptz not null default now(),
    created_at              timestamptz not null default now(),
    updated_at              timestamptz not null default now(),
    deleted                 boolean not null default false,
    version                 int not null default 0
) partition by range (stat_hour);

create table if not exists aap_usage_hourly_default partition of aap_usage_hourly default;

-- C7：用量桶唯一 UPSERT
create unique index if not exists uq_usage_hourly on aap_usage_hourly (stat_hour, channel_id, model_name, group_name);
create index if not exists idx_usage_provider_hour on aap_usage_hourly (provider_id, stat_hour desc);
create index if not exists idx_usage_channel_hour on aap_usage_hourly (channel_id, stat_hour desc);

create table if not exists aap_usage_sync_cursor (
    id              bigint primary key,
    data_source     varchar(32) not null default 'LOG_DB',
    cursor_hour     timestamptz,
    last_run_at     timestamptz,
    last_batch_id   bigint,
    status          varchar(32),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create unique index if not exists uq_usage_cursor_source on aap_usage_sync_cursor (data_source) where deleted = false;

-- ---------------------------------------------------------------- support
-- append-only：DB 层只授予 INSERT/SELECT（C8），应用层不提供 update/delete
create table if not exists aap_audit_log (
    id              bigint primary key,
    trace_id        varchar(64),
    actor_type      varchar(16) not null default 'SYSTEM',
    actor_id        bigint,
    actor_name      varchar(64),
    actor_ip        varchar(64),
    user_agent      varchar(255),
    action          varchar(64) not null,
    target_type     varchar(64),
    target_id       bigint,
    summary         varchar(500),
    before_value    jsonb,
    after_value     jsonb,
    result          varchar(16),
    risk_level      varchar(16) not null default 'NORMAL',
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create index if not exists idx_audit_trace on aap_audit_log (trace_id);
create index if not exists idx_audit_created on aap_audit_log (created_at desc, id desc);
create index if not exists idx_audit_action_created on aap_audit_log (action, created_at desc, id desc);
create index if not exists idx_audit_actor on aap_audit_log (actor_type, actor_id, created_at desc);

create table if not exists aap_notification (
    id              bigint primary key,
    recipient_type  varchar(16) not null default 'PROVIDER',
    recipient_id    bigint not null,
    channel         varchar(16) not null default 'INBOX',
    event_code      varchar(32),
    title           varchar(128) not null,
    content         text,
    biz_type        varchar(32),
    biz_id          bigint,
    category        varchar(32) not null default 'SYSTEM',
    read_at         timestamptz,
    status          varchar(32) not null default 'PENDING',
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted         boolean not null default false,
    version         int not null default 0
);
create index if not exists idx_notification_recipient on aap_notification (recipient_type, recipient_id, created_at desc, id desc);
create index if not exists idx_notification_unread on aap_notification (recipient_id, read_at);

create table if not exists aap_file_asset (
    id              bigint primary key,
    file_key        varchar(255) not null,
    bucket          varchar(64),
    original_name   varchar(255),
    content_type    varchar(128),
    size_bytes      bigint,
    sha256          char(64),
    biz_type        varchar(32),
    encrypted       boolean not null default false,
    status          varchar(32) not null default 'ACTIVE',
    expire_at       timestamptz,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    created_by      bigint,
    updated_by      bigint,
    deleted         boolean not null default false,
    version         int not null default 0
);
create unique index if not exists uq_file_key on aap_file_asset (file_key) where deleted = false;

create table if not exists aap_outbox_event (
    id                  bigint primary key,
    event_id            varchar(64) not null,
    aggregate_type      varchar(64) not null,
    aggregate_id        bigint,
    aggregate_version   int,
    event_type          varchar(16) not null,
    payload             jsonb,
    status              varchar(16) not null default 'NEW',
    attempt_count       int not null default 0,
    next_retry_at       timestamptz,
    last_error          varchar(500),
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    deleted             boolean not null default false,
    version             int not null default 0
);
create unique index if not exists uq_outbox_event_id on aap_outbox_event (event_id);
create index if not exists idx_outbox_status_retry on aap_outbox_event (status, next_retry_at, id);

create table if not exists aap_idempotency_record (
    id                  bigint primary key,
    idempotency_key     varchar(128) not null,
    actor               varchar(64),
    endpoint            varchar(128) not null,
    request_hash        char(64) not null,
    response_status     int,
    response_body       jsonb,
    state               varchar(16) not null default 'IN_PROGRESS',
    expire_at           timestamptz not null,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    deleted             boolean not null default false,
    version             int not null default 0
);
create unique index if not exists uq_idempotency_key on aap_idempotency_record (idempotency_key);
create index if not exists idx_idempotency_expire on aap_idempotency_record (expire_at);

-- ---------------------------------------------------------------- 基础字典数据（幂等）
insert into aap_role (id, code, name, scope) values
    (1001, 'SUPPLIER', '供应商', 'PROVIDER'),
    (1002, 'PROVIDER', '供应商（兼容旧值）', 'PROVIDER'),
    (1003, 'BIZ_OPERATOR', '运营商务', 'ADMIN'),
    (1004, 'TECH_OPS', '技术运营', 'ADMIN'),
    (1005, 'SUPER_ADMIN', '超级管理员', 'ADMIN')
on conflict (id) do nothing;
