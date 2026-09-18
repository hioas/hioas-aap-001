-- =====================================================================================
-- V5：配置中心（报告模板）主键与模板编号序列 —— ADM-CFG07 创建报告模板
-- 真源：docs/backend/02-API接口模型清单.md §2.4（ADM-CFG06…10）、01-ER数据模型.md §`aap_report_template`
-- 幂等：if not exists —— 重跑不报错（与 V2/V4 的既有做法一致）
--
-- 为什么用序列而不是复用 MyBatis-Flex 雪花：配置中心一律走显式 SQL（JdbcTemplate），
-- 需要数据库侧的主键与单号来源；序列并发不重号、重启不跳号。
-- =====================================================================================

-- 报告模板主键（aap_report_template.id）
create sequence if not exists seq_report_template start 1 increment 1;

-- 报告模板编号（aap_report_template.template_no，形如 TPL{yyyyMMdd}{4位}）
create sequence if not exists seq_report_template_no start 1 increment 1;
