# 任务 1（检测执行器 · 方案 A）交接单

> 交接时间：2026-09-23 · 上一会话上下文耗尽前落盘
> 用途：新会话直接读本文件即可接续，不必依赖上一会话的上下文

## 一、已完成（本会话前序，均已提交）

| 提交 | 内容 |
|---|---|
| `2effd01` | 凭证列表页状态标签可点击筛选（任务 #10） |
| `f123a77` | 凭证可删除（CRED-08 软删，后端 + 前端 + 测试） |
| `ce6ca12` | 检测记录版本化 + 重复检测策略（V10 迁移） |
| `116647a` | 「加载模型列表」保留已选勾选状态 |
| `1affa96` | 凭证页加「加载模型列表」按钮 + 三按钮移到清单下方 + 列表页点凭证名回编辑页 |
| `a21940e` | 真实渠道拉取验证脚本（new-api 中转平台） |

**基线**：后端 211/211（+删除测试 3 = 214）· aap-client 1250/1250 · type-check 0

## 二、本会话新写、**未编译未测试**的两个文件（任务 1 的核心）

```
aap-server/src/main/java/com/hioas/aap/detection/DetectionProbeRunner.java   （新，~230 行）
aap-server/src/main/java/com/hioas/aap/detection/DetectionExecutor.java      （新，~150 行）
```

- `DetectionProbeRunner`：真发 chat/completions 测 D1 TTFT / D2 时延吞吐 / D3 一致性；
  D7 指纹由子项合成；D8 以证据摘要判定；D4/D5 不主动施压配额、D6 看 cached_tokens 字段
  → 不可测项标 `NOT_MEASURABLE` 交 `summarize` 按权重再分配（PRD 09 §5 允许，**不填示意分**）
- `DetectionExecutor`：`@Scheduled` 扫 `status=QUEUED` → 置 RUNNING → 跑探针 →
  调既有 `DetectionService.recordProbeResults` 回写（打分/结论/报告/站内信沿用既有逻辑）

**⚠️ 首要动作**：`cd aap-server && mvn -o -q compile` —— 这两个文件是我凭读到的签名写的，
很可能有编译错误（例如 `JsonCodec.fromJson` / `CredentialEntity` 的 getter 名 /
`DetectionJobMapper.selectListByQuery` 是否可用，都需实测确认）。

## 三、缺陷 1 的原始证据（复现用）

```
aap_detection_job 460136577807085568
  status      QUEUED
  created_at  06:39:29
  updated_at  06:39:29      ← 与创建时间完全相同 = 插入后再没被任何代码碰过
全库：COMPLETED 18 / QUEUED 6
```

根因：`DetectionService.recordProbeResults`（该类第 270 行）**全仓零调用方**。

## 四、下一步（建议顺序）

1. `mvn -o -q compile` 修编译错误
2. 补端到端测试：造 QUEUED 任务 → 执行器跑一轮 → 断言
   `job.status=COMPLETED`、`aap_detection_result` 有行、凭证 `detection_status` 变 PASS/FAIL、
   报告与站内信产生
3. `mvn -o test` 全量回归
4. 运行态验证：重启后端 → 观察库里 6 个 QUEUED 被消费 → 目标准为 0
5. 提交

## 五、环境铁律（踩过的坑）

- **后端测试必须先注入 env**：`set -a; . /e/env/aap-server.env; set +a`
  否则报 `FATAL: password authentication failed for user "${DB_USER}"`（看着像代码错，实为缺 env）
- Maven 包装器：`export PATH="$HOME/bin:$PATH"`（原生 mvn 在 MSYS 下不可用）
- 短信 60 秒冷却：多轮脚本需 `sleep 65`；**同测试内二次取 token 必失败**（验证码一次性）
  → 每个用例用独立手机号
- **CRLF 坑**：python 多行替换须 `newline=''` 读入 + 显式拼 `\r\n` + **加 assert**
  （漏 assert 会静默不匹配，这次已犯两次）
- **回退验证用明确 SHA**，绝不用 `HEAD~1`（仓库有 cron 作业并发提交）
- 启停一律走 **IDEA MCP**（`node tools/idea-mcp-call.mjs execute_run_configuration ...`），
  联调开关走 `envs` 覆盖，不改含明文的 run config 文件

## 六、仍待用户拍板（新会话别自己定）

| # | 事项 | 待定内容 |
|---|---|---|
| 2 | 报价单卡片编辑/查看 | 我推测：草稿=可编辑，已提交/待签署/其他=只读 |
| 4 | 重复检测开关**极性** | 我按用户文字原意实现（开启=复用同一条），但与「可重复检测」名字的直觉相反 |
| 5 | 「API类型」下拉 | 后端三处无 `api_type`/`protocol` 字段 |
| 6 | 「已配置」绿标签去留 | 原型截图无此标签，但有测试守着 |
| 12 | 报价单表头不可编辑处置 | 补 PUT / UI 明示只读 / 维持现状 |
| 13 | 雪花 ID 是否全局修 | 目前只修了 catalog 视图 |
| 14 | S-1 `GET /files/{id}` 无归属校验 | 代码层已确证，运行层未复现 |
