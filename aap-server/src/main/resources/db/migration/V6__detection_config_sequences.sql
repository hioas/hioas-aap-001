-- =====================================================================================
-- V6：检测配置版本（ADM-CFG01…05）主键 / 检测项 / 版本号序列
-- 真源：docs/backend/02-API接口模型清单.md §2.4（ADM-CFG01…05）、01-ER数据模型.md
--       §`aap_detection_config`（`version_no` UQ、status DRAFT/PUBLISHED/SUPERSEDED）
--       §`aap_detection_config_probe`（probe_code D1–D8、weight 归一化前、timeout 默认）
-- 幂等：if not exists —— 重跑不报错（与 V2/V4/V5 的既有做法一致）
--
-- 为什么 `version_no` 也走序列：`uq_detection_config_version` 是**全表唯一**约束，
-- 新建即新版本（V1、V2…）。用 count(*)+1 生成在并发下会重号，序列并发安全、重启不跳号。
-- =====================================================================================

-- 检测配置主键（aap_detection_config.id）
create sequence if not exists seq_detection_config start 1 increment 1;

-- 检测项主键（aap_detection_config_probe.id）
create sequence if not exists seq_detection_config_probe start 1 increment 1;

-- 配置版本号（aap_detection_config.version_no，形如 V1、V2…）
create sequence if not exists seq_detection_config_version start 1 increment 1;
