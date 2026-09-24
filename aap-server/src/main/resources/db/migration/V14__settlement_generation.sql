-- 结算单生成闭环（D-SETTLE-02，2026-09-24）
--
-- 为什么需要这个迁移（运行态实测，非推断）：
--   `aap_settlement_statement` / `aap_settlement_line` 在本仓库此前**只有读路径**——
--   ADM-PAY03 实测 total=0、全仓 `insert into aap_settlement_statement` 零命中，即
--   「打款确认之后没有下一环」。建表时（V1 baseline）也没有配套的 ID 序列
--   （两表 id 均为 `bigint primary key` 无 default），与 V12 给同步表补序列的情形完全相同。
--   本轮补齐「生成结算单 + 明细」的写入侧，故补两条 ID 序列。
--
-- 唯一性口径（幂等 + 可重算）：
--   同一供应商同一周期**最多一份有效**结算单（status <> 'VOID'）。
--   用**部分**唯一索引而非普通唯一索引，是为了让「作废 → 重新生成」这条产品动作可行
--   （D-SETTLE-02：口径调整或用量补录后先作废再重算；历史单保留可追溯，不物理删除、不覆盖）。
--
-- 兼容性：此前该表 0 行，无历史数据冲突；序列与索引均 if not exists，可重复执行。

create sequence if not exists seq_settlement_statement_id start 1 increment 1;
create sequence if not exists seq_settlement_line_id start 1 increment 1;

create unique index if not exists uq_statement_provider_period
    on aap_settlement_statement (provider_id, period_from, period_to)
    where deleted = false and status <> 'VOID';
