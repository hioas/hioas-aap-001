# Agent 编码任务的监控与自驱循环（SDD + TDD 驱动）设计方案

> 目标：让 IDEA 插件 `ccgui`（`idea-claude-code-gui`）执行的编码任务**可判定完成、可自动续跑、可控不失控**。
> 本方案不猜插件内部实现，全部基于本机实测的事实源。

## 0. 一句话结论

**不要去问插件「完成了吗」，而要问工作区「事实是否收敛」。**

Agent 的自述不可信（LLM 会说「已完成」而测试仍红），插件 UI 状态不可编程。
唯一可靠信号是**客观证据**：测试退出码、git 差异、证据文件是否更新。

## 1. 本机实测到的事实源（2026-10 实测）

| 事实源 | 路径 | 用途 | 稳定性 |
|---|---|---|---|
| **会话转录** | `~/.claude/projects/<项目slug>/*.jsonl` | 每轮消息/工具调用/结果；判断「是否卡在等用户确认」 | 中（格式随版本变，需容错） |
| 会话数据 | `~/.claude/session-data/` | 会话级元数据 | 中 |
| 计划 | `~/.claude/plans/` | 任务计划快照 | 中 |
| 文件历史 | `~/.claude/file-history/` | 改动轨迹 | 中 |
| 桥接 | `<IDEA>/plugins/idea-claude-code-gui/ai-bridge/channel-manager.js` + `channels/` | 通道协议，可主动控制 | **低**（非公开 API） |

结论：**转录可读但易变；工作区不可骗**。故方案以工作区为主判据。

## 2. 核心机制：三态判据（Loop 的心跳）

计算**工作区指纹**：

```
F = H( git status --porcelain
     ‖ 关键产物 mtime（target/、证据目录、迁移目录）
     ‖ 最近一次门禁输出摘要 )
```

每个 tick（如 15s）比较：

| 指纹 | 门禁 | 判定 | 动作 |
|---|---|---|---|
| 在变 | — | **RUNNING** | 继续等 |
| 不变 | 绿 | **DONE** | 记账、推进下一个 Task |
| 不变 | 红 | 且超时 | **STALLED** | 回灌失败上下文 / 重启 agent / 升级人工 |

这一步就解决了「如何监控完成状态」——**不依赖插件**，换任何 agent（ccgui / claude CLI / codex）都成立。

## 3. 分层架构（五个组件，职责单一）

```
L0 任务源   specs/NNN/tasks.md  ──生成──▶  tools/loop/tasks.json
L1 执行器   ccgui（GUI） 或 claude CLI（headless，可编程，推荐后者做自驱）
L2 门禁     tools/loop/gate.sh <taskId>   → exit code + 证据文件
L3 状态机   tools/loop/loop.py            → RUNNING / DONE / STALLED + 预算 + 升级
L4 账本     .agents/loop/ledger.jsonl     → 每次尝试：时间/指纹/读数/失败摘要/证据
L5 观测     heartbeat.log + notify（Feishu / 终端 / IDE 插件）
```

**设计原则**

1. **判据外置**：完成与否由 L2 决定，不由 agent 声明。
2. **单点真相**：所有尝试写入 L4，可重放、可审计、可交叉验证。
3. **无状态驱动器**：L3 只依赖「任务定义 + 账本 + 门禁」，进程重启可续跑。
4. **同一工作区串行**：禁止并发 agent 写同一仓库（本项目的两次自我干扰即反例）。

## 4. Task 的定义（SDD + TDD 的关键约束）

一个 Task 若**没有可执行验收**，就不该进循环——因为它无法被判定完成。

```yaml
# tools/loop/tasks.json（由 tasks.md 生成）
- id: T-M4-08
  title: 限速计划
  ac: [R-57]                                   # 追溯规格条款
  red:  mvn -B test -Dtest=ConfigApplyRateLimiterTest   # 必须先红（能力缺失）
  green: mvn -B test -Dtest=ConfigApplyRateLimiterTest  # 转绿
  gate: [                                       # 完成门禁（全绿才算 DONE）
    mvn -B -ntp test,                           # 全量回归
    mvn -B -ntp test -Dtest=EndpointCoverageTest,  # 契约冻结
    mvn -B -ntp test -Dtest=MigrationTest       # 迁移/ER 文档一致
  ]
  evidence_dir: .agents/state/evidence
  max_attempts: 3
  budget_minutes: 40
```

**DONE 的判定（四条同时成立）**

1. `green` 退出码 0；
2. `gate` 全部退出码 0；
3. 证据文件存在，且 `mtime > task.start_time`；
4. `git diff` 非空。

> 第 3、4 条是最关键的两个**反作弊**约束——挡住「agent 说完成了但没干活」和「拿历史绿报告冒充本轮」。

## 5. 「一直 loop」的正确形态

⚠️ **`while(true)` 是反模式**：烧预算、掩盖真问题、把「卡住」伪装成「在努力」。

正确形态 = **有界重试 + 上下文返工 + 升级**：

```
for task in tasks:
    start = now()
    for attempt in 1..task.max_attempts:
        if gate.passed(task): break
        ctx = last_failure_excerpt(gate)        # ← 关键：把红输出喂回去
        agent.run(task, context=ctx)            # 不是重复同一句提示
        if now() - start > task.budget: break
    if gate.passed(task):
        ledger.record(task, "DONE", attempts)
    else:
        ledger.record(task, "ESCALATED", reason)
        notify_human(task)                      # 转人工，不无限重试
```

**两个提升成功率的设计**

- **失败上下文回灌**：把失败的测试名、断言差异、编译错误截取 20–40 行喂回，比「再试一次」有效得多。
- **失败模式分类**（来自本项目的实践）：
  - 权限/鉴权类 → 重试无意义，直接升级；
  - 编译/类型错误 → 可直接返工；
  - 环境/端口/代理类 → **先修环境再重试**（否则会把环境故障误当成代码缺陷）。

## 6. ccgui 的三种接入方式（按侵入度递增）

| 方式 | 做法 | 优点 | 缺点 | 建议 |
|---|---|---|---|---|
| **A 黑盒（主）** | 监控工作区指纹 + 门禁 | 与插件/agent 解耦；换工具不换方案 | 看不到 agent 内部思考 | ✅ 主方案 |
| **B 读转录（辅）** | 解析 `~/.claude/projects/<slug>/*.jsonl` | 能看出「在等用户确认」还是「真在跑」 | 格式随版本变 | ✅ 用于区分 STALLED 原因 |
| **C 桥接 API** | 用 `ai-bridge` 的 channel 协议主动控制 | 最准、可发指令 | 非公开 API，升级即破 | ⚠️ 不作生产依赖 |

**A + B 组合的价值**：A 判断「是否完成」，B 判断「为什么没完成」（等确认 / 工具报错 / 空转）。

## 7. 与本项目现有资产的复用

| 已有资产 | 在方案中的角色 |
|---|---|
| `specs/NNN/tasks.md`（含 DoD/依赖） | L0 任务源 |
| TDD 红/绿证据（`.agents/state/evidence/{red,green}-*.txt`） | L2 门禁产出 |
| `MigrationTest` / `EndpointCoverageTest`（双向断言门禁） | gate 的必跑项 |
| `tools/round-verify/run-round.sh` 等 | L2/L3 的雏形，可直接扩成 loop 驱动器 |
| 提交卫生（逐路径 add、不碰他方在制品） | L3 的写入约束 |

## 8. 落地清单（最小可用 → 完整）

| 阶段 | 交付 | 判定标准 |
|---|---|---|
| M1 | `tools/loop/fingerprint.py` + `gate.sh` | 能对一个 Task 输出 DONE/红 |
| M2 | `loop.py`（三态 + 账本 + 有界重试） | 无人值守跑完 3 个 Task，账本完整 |
| M3 | 失败上下文回灌 + 失败模式分类 | 同一 Task 二次尝试成功率显著提升 |
| M4 | 通知 + 转录解析（B） | STALLED 能给出原因（等确认/报错/空转） |
| M5 | 与 SDD 全量特性绑定 | 一个特性（spec）从 AC 到全部 Task DONE 全自动 |

## 9. 风险与边界

- **不追求「全自动到生产」**：门禁绿 ≠ 业务正确，仍需人做验收标准设计与最终 review。
- **不无限重试**：`max_attempts` 与时间预算是硬约束，超限转人工。
- **转录格式不稳定**：B 方式只作辅助判断，失败时降级为「未知原因」而不是误判。
- **并发是毒药**：同一工作区只允许一个 agent 写；否则指纹、证据、提交都会互相污染（本项目实测踩过）。
- **环境故障与代码缺陷必须分开**：代理 502、端口占用、SSRF 白名单这类问题若被当成代码缺陷，会让人在错误方向上改代码（本项目实测踩过）。
