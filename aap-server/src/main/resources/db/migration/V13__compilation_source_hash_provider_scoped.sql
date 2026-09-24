-- 修复：编译产物 source_hash 的唯一性口径（R-34 幂等）
--
-- 现象（闭环联调实测复现，非推断）：
--   `POST /admin/quotes/{id}/compile` 在「同一供应商的**第二张报价单**内容相同」以及
--   「两个供应商报出相同价格」两种情形下，均以
--     duplicate key value violates unique constraint "uq_compilation_source_hash" → E-2001
--   失败（dev 库 traceId ad5d1793ccdd4df784bc76783fec8aa2 / bccf95ebe63e430fa71d41d4a3ea3f7f）。
--
-- 根因：两处口径不一致 ——
--   * `uq_compilation_source_hash` 是**全表唯一**（`where deleted = false`，不含 provider 维度）；
--   * `BillingCompiler.sourceHash(items)` 只由**计价规则内容**构成（模型名/价格/档位/时段），
--     不含 provider_id。
--   ⇒ 只要两个供应商（或同一供应商两张报价单）内容相同，hash 就相同，第二笔必然撞索引。
--   而 `CompilationService.compile` 的幂等查询是 `(quote_id, source_hash)` 粒度，命中不了这条记录，
--   于是直接走到 insert 上爆炸。
--
-- 修法：把唯一性收敛到编译产物真正的归属维度 —— **(provider_id, source_hash)**。
--   编译产物本身是供应商专属的（`previous_expr` / `confirmed_by` / 表达式都按供应商维度组织），
--   跨供应商共用一条产物既不合语义，也会造成越权复用（供应商 B 拿到 A 的确认状态）。
--   配套：`CompilationService.compile` 的幂等查询同步改为 provider_id + source_hash（见该类注释）。
--
-- 兼容性：旧索引删除后，历史上同一 provider 不存在重复 hash 的数据（insert 一直被索引挡着），
--   故新索引可直接建立；不同 provider 之间的重复 hash 在新口径下合法且必需。

drop index if exists uq_compilation_source_hash;

create unique index if not exists uq_compilation_provider_source_hash
    on aap_compiled_expression (provider_id, source_hash)
    where deleted = false;
