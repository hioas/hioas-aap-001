-- =====================================================================================
-- V4：用量域主键与聚合批次序列（幂等：if not exists）
-- 真源：docs/backend/01-ER数据模型.md §4.9 `aap_usage_hourly`（id 雪花/批次号）、`aap_usage_sync_cursor.last_batch_id`
--
-- 为什么用序列而不是复用 MyBatis-Flex 雪花：用量域全是「GROUP BY 聚合 + UPSERT」的显式 SQL
-- （见 UsageService 设计取舍①），走 JdbcTemplate 时需要数据库侧的主键来源；
-- 序列并发不重号、重启不跳号，与 V2 的既有做法一致。
-- =====================================================================================

-- 小时桶主键（aap_usage_hourly.id）
create sequence if not exists seq_usage_hourly start 1 increment 1;

-- 聚合批次号（aap_usage_sync_cursor.last_batch_id / 响应 batch_id）
create sequence if not exists seq_usage_batch start 1 increment 1;
