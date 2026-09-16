---
name: dev
description:  dev（develop env verify）开发环境验证，任何项目(Java/Vue/Go/Python/...)在本地idea内的「编译 + 启动 + 测试 + 浏览器验证」标准流程：应用一律经 IDE MCP 启动；中间件复用优先——先查运行中容器与 E:\docker\dev\*\docker-compose.yml(windows环境下docker通过wsl启动，wsl中路径为/mnt/e/docker/dev/...)或~/workspace/docker/dev/*/docker-compose.yml(macos|linux环境)是否已有，已有直接复用、不重复起同类型容器，确无才在该目录补齐目录与 docker-compose.yml；启动后核对日志（无日志文件先补配置），有错即改直到全部服务启动成功；通过后再根据标准化分支名（如dev.1.0.260910或prd.1.0.260910）创建Dockerfile并在项目的docker文件夹下创建如：docker/[dev,prd]/[.env,docker-compose.yml,其他配置等],镜像名按项目名:分支名；服务全绿后用 MCP 浏览器工具（cua/playwright/cdp 等，无则降级 webapp-testing）以有头模式打开页面、走主链路并截图留证。当用户说「启动/运行/联调/跑起来/测试验证/可视化验证/打开浏览器测试」时使用。
---

# SKILL · 应用启动与测试验证标准流程（指针）

> **本文件不是作业标准，只是入口指针。** 唯一真源在跨 agent 目录：

**真源 → [`../../../.agents/skills/dev/SKILL.md`](../../../.agents/skills/dev/SKILL.md)**

路径相对本文件解析、上溯到仓库根再进入 `.agents/`，因此**随仓库克隆/迁移位置自动生效，不含任何绝对路径**，Windows / Linux / macOS 一致。

---

## 使用要求（必须）

1. 触发本 skill 后，**先完整读取上述真源文件**，再开始任何动作。
2. 流程步骤、中间件与日志规范、排错手册、模板、验收 DoD、安全红线**一律以真源为准**。
3. 本文件**不复述真源任何条目**——一旦复述就会再次分叉。唯一例外是 frontmatter 的 `description`：Claude Code 靠它决定何时触发，因此它与真源 description **必须逐字一致**，改一侧就得改另一侧。
4. 项目自身的架构与不变式见 [`SOUL.md`](../../SOUL.md)（项目宪法）。冲突时：**领域约束依 SOUL，流程约束依真源，不得放松。**

---

> 真源与本文曾各存一份全文（v1.0 / v1.1），结果 v1.1 新增的「浏览器可视化验收」只落到一侧、`SOUL.md` 链接在另一侧成断链。
> **改动 SOP 只改真源**，不要把内容复制回本文件。
