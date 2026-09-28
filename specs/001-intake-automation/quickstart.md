# quickstart · 进件自动化验收场景

> 配套 `spec.md`。本文给出**可执行**的验收路径：每个场景说明前置、操作、判定与证据落点。
> 全部场景必须产出真实运行输出，禁止以「编译通过」代替（宪法 D-07）。

---

## 0. 环境前置

| 项 | 值 |
| --- | --- |
| 仓库 | `E:/workspaces/hioas/hioas-aap-001` |
| 后端（dev） | 端口 `8086`（启动器：`tools/with-env.sh` 内层覆盖 `SERVER_PORT`） |
| 管理端（dev） | 端口 `5175`，`AAP_API_TARGET=http://127.0.0.1:8086` |
| 网关（本地一体桩） | 端口 `9911`（`tools/newapi-stub.py`，**明确非交付路径**） |
| 数据库 | PostgreSQL（dev 库），查询经 `wsl bash -lc 'bash tools/dev-db-query.sh "..."'` |
| 管理端账号 | 超管手机号 `13800000221` |
| 供应商账号 | `13800138000` |
| 环境变量 | `tools/with-env.sh aap-server <cmd>`（凭据只打印变量名，不打印值） |

启动（各自独立会话）：

```bash
# 后端
bash tools/with-env.sh aap-server bash -c 'SERVER_PORT=8086 mvn -q -pl aap-server spring-boot:run'
# 管理端
cd aap-admin && AAP_API_TARGET=http://127.0.0.1:8086 npm run dev -- --port 5175
# 网关桩
python tools/newapi-stub.py --port 9911
```

---

## 场景 1 · 一模型一渠道的进件全自动（AC-01 / AC-02 / AC-03）

**前置**：供应商 `13800138000` 提交一份含 **3 个模型**的凭证，检测 PASS，合同签署并打款确认。

**操作**：

```bash
python tools/biz-closure-e2e.py --report .agents/state/evidence/intake-automation.json
```

**判定**：

| 步 | 期望 |
| --- | --- |
| 1 | 供给单元展开为 **3 条**（`模型 × 供应商`） |
| 2 | 网关侧创建 **3 条**渠道，命名形如 `AAP-<short>-<model_slug>`，互不相同 |
| 3 | 每条渠道的 `models` 字段**只含 1 个模型** |
| 4 | 回读校验：名称 / `base_url` / `models` / `status` / `priority` / `weight` 全部一致（3/3） |
| 5 | 重复执行配置步骤 → 渠道总数**不变**（幂等） |

**证据**：`.agents/state/evidence/intake-automation.json`（含逐步 detail）；
库侧核对：

```bash
wsl bash -lc 'cd /mnt/e/workspaces/hioas/hioas-aap-001 && bash tools/dev-db-query.sh \
  "select count(*), bool_and(models !~ \",\") from aap_channel_binding where granularity = '"'"'PER_MODEL'"'"' and deleted = false"'
```

---

## 场景 2 · 部分失败与单模型隔离（AC-04 / AC-05）

**前置**：3 个模型中第 2 个的上游地址不可达。

**判定**：

| 步 | 期望 |
| --- | --- |
| 1 | 第 1、3 条渠道创建成功且回读一致 |
| 2 | 第 2 条标记 `FAILED`，**其余两条不受影响**（R-59） |
| 3 | 该供给单元标记「配置未收敛」并在控制台可见 |
| 4 | 单模型重试接口（`ADM-CFG04`）可只重试第 2 条并成功 |

**另测（AC-05）**：让某模型上游持续返回错误 → 该渠道被网关自动禁用（`auto_ban`），
同供应商其他模型渠道仍为启用状态。

---

## 场景 3 · 同模型多供应商分流（AC-06）

**前置**：两个供应商都提供同一模型。

**判定**：创建两条渠道（不同 `short_code`，同一 `model_slug`）；
按 `priority`/`weight` 分流，可通过网关用量按渠道分布观察流量比例。

---

## 场景 4 · dry-run 零写入（AC-10）

**操作**：

```bash
curl -sS -X POST "$API/api/v1/admin/config-batches" \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"batchType":"ADD_CHANNEL","mode":"DRY_RUN","scope":{"providerIds":[1]},"reason":"验收预演"}'
```

**判定**：

| 步 | 期望 |
| --- | --- |
| 1 | 响应含 `diffPayload`（将创建/变更的清单） |
| 2 | 网关侧渠道数**完全不变**（预演前后各取一次快照比对） |
| 3 | 库内 `aap_config_batch_item` 无 `SUCCEEDED` 写入项（或写入项数为 0） |

---

## 场景 5 · 调价、比价、毛利与漂移（AC-08 / AC-09 / AC-12 / AC-13 / AC-14）

| 步 | 操作 | 期望 |
| --- | --- | --- |
| 1 | 供应商对某模型输入价 **+10%** 并提交报价 | 报价 → 编译 → 写入 → 回读全通；渠道价格表出现新价与来源版本 |
| 2 | 用一份**未过闸门②**的报价尝试写入 | 拒绝，错误定位到具体规则字段；渠道价格表**不出现**该价（AC-09） |
| 3 | 管理端对某模型批量调价 +10%（dry-run） | 返回影响面：渠道数 / 供应商数 / 预估金额 |
| 4 | 查看该模型的渠道价格矩阵 | 各供应商生效价排序 + 相对基准价溢价/折价（AC-13） |
| 5 | 查看毛利视图 | 采购价与对外价之差按模型聚合 |
| 6 | 把某供给单元上游价改成偏差 8% | 漂移看板告警；连续两周期未处理自动降权（AC-14） |

---

## 场景 6 · 脱敏与越权（AC-18 / AC-19）

| 步 | 期望 |
| --- | --- |
| 1 | 对后端日志、`aap_audit_log`、`aap_config_batch_item.request_summary` 全文扫描 `sk-` 与 `Bearer` | **零命中**（AC-18） |
| 2 | 用供应商 A 的令牌访问供应商 B 的供给单元 | 返回与「不存在」**相同**的结果（404 `E-1406`，AC-19） |
| 3 | 管理端页面显示的价格与用量 | 与库内 `aap_channel_price` / `aap_usage_hourly` 一致 |

---

## 场景 7 · 自动化等级与高风险拦截（AC-17）

| 前置 | 期望等级 |
| --- | --- |
| AGGREGATOR + 指纹置信度 LOW | **L1**（必须人工确认，禁止自动写生产） |
| ORIGINAL + PASS + 标准模型 + 金额低于阈值 | 允许 **L3** |
| 首次接入该供应商 | 禁止 L3（R-61） |

---

## 8. 验收清单（AC 对照）

| AC | 场景 | 证据 |
| --- | --- | --- |
| AC-01/02/03 | 场景 1 | `intake-automation.json` + 库侧核对 |
| AC-04/05 | 场景 2 | 批次明细（含 `FAILED`/`MISMATCH`）+ 网关状态 |
| AC-06 | 场景 3 | 网关用量按渠道分布 |
| AC-07 | 重配置（换 key） | 批次明细前后对比（脱敏） |
| AC-08/09 | 场景 5 步 1–2 | 渠道价格表历史 + 拒绝错误体 |
| AC-10 | 场景 4 | 预演前后网关快照比对 |
| AC-11 | 批量 100 条 | 执行日志（限速与退避记录） |
| AC-12/13/14 | 场景 5 步 3–6 | 影响面响应 + 矩阵/毛利视图 + 漂移记录 |
| AC-15 | 供给覆盖降到 1 | 告警记录 |
| AC-16 | 复测降级 | 权重变更记录 + 通知 |
| AC-17 | 场景 7 | 自动化判定记录 |
| AC-18/19 | 场景 6 | 扫描输出 + 越权响应体 |
| AC-20 | 合并模式 | 渠道列表（命名不冲突校验） |

---

## 9. 门禁与回归（本特性上线前必须全绿）

| 门禁 | 命令 | 期望 |
| --- | --- | --- |
| 后端全量 | `bash tools/with-env.sh aap-server mvn -B -ntp test` | 0 失败（263 → 新增本特性用例） |
| 端点覆盖 | 同上（含 `EndpointCoverageTest`） | 冻结清单 = **137** |
| 管理端门禁 | `node aap-admin/tools/admin-acceptance.mjs http://127.0.0.1:5175 <账号>` | 全绿 + 新增页面判据 |
| 管理端单测 | `cd aap-admin && npm test` | 0 失败 |
| 供应商端单测 | `cd aap-client && npm test` | 0 失败 |
| 端到端 | `python tools/biz-closure-e2e.py --report <证据文件>` | 全步通过（含新增 P11 段） |
| 巡检不变量 | `tools/round-verify/run-round.sh RNNN` | 40 类不变量零违规（含新增：供给单元↔渠道 1:1、价格生效唯一、dry-run 零写入） |
