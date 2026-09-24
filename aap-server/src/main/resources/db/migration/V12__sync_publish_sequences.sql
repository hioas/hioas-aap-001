-- 上架同步闭环（ADM-S07/S08/S09，2026-09-24）所需的 ID 序列。
--
-- 为什么新建：`aap_newapi_endpoint` 与 `aap_channel_binding` 此前**只有读路径**（写入侧缺失，
-- 见 aap-decisions.md D-SYNC-03），因此 V1 baseline 里两张表都没有配套序列。补写入侧时，
-- id 生成沿用本项目 JdbcTemplate 写路径的既有做法（`nextval('seq_...')`），与
-- `seq_sync_task` / `seq_sync_operation` 同族。
--
-- 幂等：`if not exists`，可重复执行（与 V2/V4/V5/V6/V7 同写法）。

create sequence if not exists seq_newapi_endpoint start 1 increment 1;
create sequence if not exists seq_channel_binding start 1 increment 1;
