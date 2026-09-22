-- 检测记录版本化 + 重复检测策略
--
-- 背景（用户口径 2026-09-23）：
--   「每次提交…之前的检测记录一个版本记录，重新提交的也是一条新纪录，
--     都执行检测的具体模型；
--     后台配置是否可重复检测：如果没开，重复提交同一凭证+同一模型 → 生成重复的检测；
--     如果开启，同一凭证下的同一模型多次提交 → 指向同一条检测。」
--
-- ⚠️ 命名说明：用户口中叫「可重复检测」，但其描述的极性与字面直觉**相反**
--    （开启 ⇒ 复用同一条 / 没开 ⇒ 每次新建）。为免后人误用，
--    本列按**行为**命名 `reuse_existing_detection`（复用已有检测结果），
--    并在下方注释保留用户原始口径以便回溯。

-- ① 检测任务记录「本次检测覆盖的具体模型」——版本记录的核心内容
ALTER TABLE aap_detection_job ADD COLUMN IF NOT EXISTS model_list jsonb;

COMMENT ON COLUMN aap_detection_job.model_list IS
    '本次检测覆盖的具体模型清单快照（渠道拉取结果）。每条检测记录都留痕，供版本比对。';

-- ② 检测配置：重复检测策略（按行为命名）
ALTER TABLE aap_detection_config ADD COLUMN IF NOT EXISTS reuse_existing_detection boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN aap_detection_config.reuse_existing_detection IS
    'true=同一凭证+同一模型集合重复提交时**指回同一条**检测记录（去重）；'
    'false=每次都生成**新的一条**检测记录（默认）。'
    '对应产品口径「是否可重复检测」（用户 2026-09-23）。';

-- ③ 去重查询支撑：按凭证 + 模型集合找既有任务
CREATE INDEX IF NOT EXISTS idx_detection_job_credential_active
    ON aap_detection_job (credential_id, active_flag)
    WHERE deleted = false;
