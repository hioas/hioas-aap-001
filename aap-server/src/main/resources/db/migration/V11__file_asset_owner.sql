-- 文件资产归属（S-1 越权修复：GET /files/{id} 无归属校验）
--
-- 背景（2026-09-23 代码层复核 + 本次处置）：
--   aap_file_asset 此前**没有归属列**，下载端点只做「按 id 取文件」（任何已登录主体都能调），
--   于是供应商 A 只要猜到/枚举到供应商 B 的文件 id，就能下载他人的合同、资质原件 —— 属越权（IDOR）。
--   「归属校验交给各业务域自己做」这条注释在本端点上无法成立：业务域只持有 file_id，
--   端点本身不校验，等于没有校验。
--
-- 处置：
--   ① 上传时记录归属（owner_provider_id，管理端上传则为 null）与上传者账号（留痕，不参与鉴权）；
--   ② 下载时校验：管理端放行 / 供应商只放行自己的 / 无归属（管理端上传，如平台签发的合同）放行。
--      规则真源写在 FileService#loadForDownload。
--
-- 存量数据：dev 库上线前复核该表 0 行，故无回填；新上传即刻带上归属。
-- 注：本列为可空 —— 既有生产数据（若有）与「管理端上传」都表现为 null，语义为「对所有已登录方可见」。

alter table aap_file_asset add column if not exists owner_provider_id bigint;
alter table aap_file_asset add column if not exists uploaded_by_account_id bigint;

comment on column aap_file_asset.owner_provider_id is
    '归属供应商 id（上传者）；null = 管理端上传（平台签发的合同等，对所有已登录方可见）';
comment on column aap_file_asset.uploaded_by_account_id is
    '上传者账号 id（供应商账号或管理端账号）——仅留痕，不参与鉴权（供应商账号 id 与 provider id 不同域）';

create index if not exists idx_file_asset_owner on aap_file_asset (owner_provider_id);
