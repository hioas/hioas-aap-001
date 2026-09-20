-- =====================================================================================
-- V9：模型目录（厂商 + 模型）—— 解开 D-ADM-3「模型管理整页无后端能力」
-- 真源：Calicat 设计 page-3「模型管理 · 按厂商分组」/ page-3-1「新增厂商」/ page-3-2「新增模型」
--       .calicat/prd/13-管理端PRD.md
-- 幂等：if not exists —— 重跑不报错（与 V2/V4/V5/V6/V7/V8 既有做法一致）
--
-- 为什么需要这两张表（用户 2026-09-20 指令）：
--   管理端「新增模型」此前**后端零能力**（全仓只有 GET /admin/sync/models/upstream，
--   实测 E-1501 未配置 ACTIVE new-api 端点），前端只能标注「后端未提供接口」。
--   而这份目录的真正消费方是 **H5 端「接入凭证」页的模型下拉**：
--   供应商接入凭证时要能从目录里挑模型；没有目录，凭证的 model_list 只能靠预检事后回填。
--
-- ⚠️ 待裁定 D-ADM-4（不静默选边）：价格单位两处不一致 ——
--   本设计（page-3-2）标注「输入价格 / 输出价格（元 / 1K tokens）」，示例 0.0011 / 0.0044；
--   而 H5 报价链（page-9 / PRD 10）用的是「$ / 1M token」，示例 2.5 / 10。
--   币种（CNY vs USD）与量纲（1K vs 1M）**双重不一致**。本表按设计原样落库
--   （input_price / output_price + currency 显式记录币种），**不做隐式换算**；
--   换算规则与以哪边为准需产品裁定后再补迁移/转换层。
-- =====================================================================================

create sequence if not exists seq_vendor start 1 increment 1;
create sequence if not exists seq_model_catalog start 1 increment 1;

-- -------------------------------------------------------------------------------------
-- 厂商（设计 page-3-1「新增厂商」）
-- -------------------------------------------------------------------------------------
create table if not exists aap_vendor (
    id                bigint primary key,
    name              varchar(128) not null,
    vendor_key        varchar(64)  not null,
    vendor_type       varchar(32)  not null,
    region            varchar(32),
    website           varchar(255),
    base_url          varchar(255) not null,
    api_key_cipher    varchar(512),
    default_qps       integer,
    currency          varchar(8),
    enabled           boolean      not null default true,
    description       text,
    created_at        timestamptz  not null default now(),
    updated_at        timestamptz  not null default now(),
    created_by        bigint,
    updated_by        bigint,
    deleted           boolean      not null default false,
    version           integer      not null default 0
);

comment on table aap_vendor is '模型厂商（Calicat page-3-1 新增厂商；供管理端维护、H5 凭证页选模型）';
comment on column aap_vendor.vendor_key is '厂商标识（英文 key，如 mistral）—— 模型标识的命名前缀来源';
comment on column aap_vendor.vendor_type is '厂商类型：DIRECT 官方直连 / THIRD_PARTY 第三方代理 / SELF_GATEWAY 自建网关';
comment on column aap_vendor.api_key_cipher is '默认 API Key（加密存储，可在单模型覆盖）—— 绝不明文落库，读取时脱敏';
comment on column aap_vendor.currency is '结算币种（CNY/USD）—— 见本文件头部 D-ADM-4，与价格单位一并待裁定';

-- vendor_key 唯一（仅未删除行）：设计里它是模型的命名前缀，重复会让模型标识二义
create unique index if not exists uk_vendor_key on aap_vendor (vendor_key) where deleted = false;

-- -------------------------------------------------------------------------------------
-- 模型（设计 page-3-2「新增模型」）
-- -------------------------------------------------------------------------------------
create table if not exists aap_model (
    id                 bigint primary key,
    vendor_id          bigint       not null,
    model_name         varchar(128) not null,
    model_uid          varchar(128) not null,
    model_type         varchar(32)  not null,
    context_window     integer,
    max_output         integer,
    input_price        numeric(18, 6),
    output_price       numeric(18, 6),
    capabilities       jsonb,
    base_url           varchar(255),
    api_key_cipher     varchar(512),
    enabled            boolean      not null default true,
    remark             text,
    created_at         timestamptz  not null default now(),
    updated_at         timestamptz  not null default now(),
    created_by         bigint,
    updated_by         bigint,
    deleted            boolean      not null default false,
    version            integer      not null default 0
);

comment on table aap_model is '模型目录（Calicat page-3-2；H5 端「接入凭证」的模型下拉数据源）';
comment on column aap_model.model_name is '模型名称（展示用，如 GPT-4o mini）';
comment on column aap_model.model_uid is '模型标识（英文标识，如 gpt-4o-mini）—— 进 model_list 的就是它';
comment on column aap_model.model_type is '模型类型：CHAT 对话 / REASONING 推理 / EMBEDDING 向量 / IMAGE 图像 / AUDIO 语音';
comment on column aap_model.capabilities is '能力标签多选（FUNCTION_CALL/VISION/JSON_MODE/STREAM/LONG_TEXT/DEEP_REASONING），用于路由与筛选';
comment on column aap_model.input_price is '输入价格 —— ⚠️ 单位口径见本文件头部 D-ADM-4（设计标 元/1K，H5 用 $/1M），未做换算';
comment on column aap_model.api_key_cipher is '单模型 API Key（覆盖厂商默认；加密存储，仅管理员可见）';

-- model_uid 唯一（仅未删除行）：同一标识不能挂两个模型，否则凭证 model_list 二义
create unique index if not exists uk_model_uid on aap_model (model_uid) where deleted = false;
create index if not exists idx_model_vendor on aap_model (vendor_id) where deleted = false;
