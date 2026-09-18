-- =====================================================================================
-- V8：供应商暂停留痕「暂停前状态」（ADM-P02 暂停 / ADM-P03 恢复）
-- 真源：docs/backend/02-API接口模型清单.md §2.4（ADM-P02/P03）、
--       01-ER数据模型.md §`aap_provider`（status 12 态 + published_at/suspended_at/suspend_reason 留痕）
-- 幂等：if not exists —— 重跑不报错（与 V2/V4/V5/V6/V7 既有做法一致）
--
-- 为什么单列一列：恢复（ADM-P03）必须回到「暂停前状态」，而 aap_provider 只留了暂停**时刻**
-- （suspended_at），没有暂停前**状态**；仅凭 status + suspended_at 无法区分「暂停前是 DETECT_PASSED
-- 还是 PUBLISHED」。宁可加一列显式留痕，也不写「一律回 PUBLISHED」这种把状态机猜错的规则
-- （偏差 D-ADM-01）。暂停时写入、恢复时读回并清空，避免下一次暂停复用旧值。
-- =====================================================================================

alter table aap_provider add column if not exists status_before_suspend varchar(32);
comment on column aap_provider.status_before_suspend is '暂停前的状态（ADM-P02 写入 / ADM-P03 恢复后清空）';
