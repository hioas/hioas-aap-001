-- =====================================================================================
-- V7：new-api 同步运维（ADM-S01…06）主键序列
-- 真源：docs/backend/02-API接口模型清单.md §2.4（ADM-S01…06）、01-ER数据模型.md
--       §`aap_sync_operation`（任务操作明细：读前写后三段式留痕）、§`aap_sync_task`、§`aap_channel_binding`
-- 幂等：if not exists —— 重跑不报错（与 V2/V4/V5/V6 的既有做法一致）
--
-- 为什么需要：ADM-S03 的每次重试都会追加一行 aap_sync_operation；该表 id 是裸 bigint 主键，
-- 走 JdbcTemplate 写入时需要数据库侧的主键来源（雪花由 MyBatis-Flex 实体侧生成，本模块
-- 全程显式 SQL，与 DetectionConfigService / UsageService 同一取舍）。
-- =====================================================================================

-- 同步操作明细主键（aap_sync_operation.id）
create sequence if not exists seq_sync_operation start 1 increment 1;
