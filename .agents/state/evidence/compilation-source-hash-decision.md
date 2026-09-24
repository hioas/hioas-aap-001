
---

## D-COMP-01 · 编译产物 `source_hash` 唯一性口径修复 —— `已实施 2026-09-24`（闭环联调中实测发现）

> 发现方式：`tools/biz-closure-e2e.py` **第二次**跑端到端闭环（第一次因为库里已有同内容产物）
> 时，`POST /admin/quotes/{id}/compile` 返回 `E-2001 内部错误`。这不是脚本问题，是真实缺陷。

**现象（可复现）**：同一供应商的**第二张报价单**（内容与第一张完全相同）、以及**两个不同供应商**
报出相同价格时，编译均失败：

```
org.springframework.dao.DuplicateKeyException:
  ERROR: duplicate key value violates unique constraint "uq_compilation_source_hash"
  Key (source_hash)=(32329e3dcfb064c54a98bad6bcb156d655604f2081a4bb1980aa0dcc6cd0f4c2) already exists
  at com.hioas.aap.compile.CompiledExpressionMapper.insert
```

**根因（两处口径不一致）**：

| 位置 | 口径 |
| --- | --- |
| 唯一索引 `uq_compilation_source_hash`（V1 baseline:863） | **全表唯一**（`where deleted = false`，**不含** provider 维度） |
| `BillingCompiler.sourceHash(items)` | 只由**计价规则内容**构成（模型名/价格/档位/时段），**不含** provider_id |
| `CompilationService.compile` 的幂等查询 | `(quote_id, source_hash)` 粒度 |

⇒ 内容相同 ⇒ hash 相同 ⇒ insert 必撞全表唯一索引；而幂等查询的 `quote_id` 粒度**命中不到**那条记录，
于是绕过幂等直接 insert → 500。业务上这很常见：供应商改一版再报、或两个供应商报同一个热门模型同价。

**修法（已实施）**：

1. `V13__compilation_source_hash_provider_scoped.sql`：删除全表唯一索引，改为
   **`(provider_id, source_hash)` 唯一**（`uq_compilation_provider_source_hash`）——
   编译产物本就按供应商维度组织（`previous_expr` / `confirmed_by` 都是供应商语义）。
2. `CompilationService.compile` 幂等查询同步改为 `provider_id + source_hash`：
   既避免漏命中撞索引，也避免**跨供应商误复用**（供应商 B 免费拿到 A 已确认的产物）——那是越权。

**验证**：`CompilationContractTest` 新增两例回归（红 → 绿）：

* `compileReusesArtifactAcrossQuotesOfSameProvider` —— 同供应商换报价单、内容相同 → 复用既有产物，HTTP 200；
* `compileIsolatesIdenticalContentAcrossProviders` —— 两个供应商同内容 → 各自独立产物，互不复用。

红基线：`Tests run: 9, Failures: 2`（两例均为 `E-2001`）；修复后：`Tests run: 9, Failures: 0`。
证据：`.agents/state/evidence/red-compilation.txt` / `green-compilation.txt`。
