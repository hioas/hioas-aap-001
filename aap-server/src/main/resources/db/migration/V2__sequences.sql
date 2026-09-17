-- =====================================================================================
-- V2：业务单号序列 + 文档号生成（幂等：if not exists）
-- 真源：17-spec §3（provider_code AAP-P-{6位}）/ 10-PRD §3.1（quote_no Q{yyyyMMdd}{6位序列}）
-- =====================================================================================

create sequence if not exists seq_provider_code start 1 increment 1;
create sequence if not exists seq_provider_no start 1 increment 1;
create sequence if not exists seq_detection_job start 1 increment 1;
create sequence if not exists seq_report start 1 increment 1;
create sequence if not exists seq_quote start 1 increment 1;
create sequence if not exists seq_contract start 1 increment 1;
create sequence if not exists seq_statement start 1 increment 1;
create sequence if not exists seq_sync_task start 1 increment 1;
create sequence if not exists seq_settlement_line start 1 increment 1;
