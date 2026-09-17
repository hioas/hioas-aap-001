-- =====================================================================================
-- V3：管理端账号补手机号三件套（支撑「凭证明文访问需超管 + 短信二次验证」，AC-30/R-05）
-- 幂等：add column if not exists —— 重跑不报错
-- =====================================================================================

alter table aap_admin_user add column if not exists phone_cipher text;
alter table aap_admin_user add column if not exists phone_hash char(64);
create index if not exists idx_admin_phone_hash on aap_admin_user (phone_hash);
