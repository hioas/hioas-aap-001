---
name: dev
description:  dev（develop env verify）开发环境验证，任何项目(Java/Vue/Go/Python/...)在本地idea内的「编译 + 启动 + 测试 + 浏览器验证」标准流程：应用一律经 IDE MCP 启动；中间件复用优先——先查运行中容器与 E:\docker\dev\*\docker-compose.yml(windows环境下docker通过wsl启动，wsl中路径为/mnt/e/docker/dev/...)或~/workspace/docker/dev/*/docker-compose.yml(macos|linux环境)是否已有，已有直接复用、不重复起同类型容器，确无才在该目录补齐目录与 docker-compose.yml；启动后核对日志（无日志文件先补配置），有错即改直到全部服务启动成功；通过后再根据标准化分支名（如dev.1.0.260910或prd.1.0.260910）创建Dockerfile并在项目的docker文件夹下创建如：docker/[dev,prd]/[.env,docker-compose.yml,其他配置等],镜像名按项目名:分支名；服务全绿后用 MCP 浏览器工具（cua/playwright/cdp 等，无则降级 webapp-testing）以有头模式打开页面、走主链路并截图留证。当用户说「启动/运行/联调/跑起来/测试验证/可视化验证/打开浏览器测试」时使用。
---

# SKILL · 应用启动与测试验证标准流程

> 本文件是本工作区**跨项目**的启动/验证作业标准（SOP）。
> 项目自身的架构与不变式见同目录 [`SOUL.md`](../../SOUL.md)(项目宪法，如无可忽略)。两者冲突时:**领域约束依 SOUL,流程约束依本文件,不得放松。**

**版本**：v1.2 · 2026-09-12 · 维护：随每次实战迭代

---

## 0. 目的与适用

**目的**：任何项目的「启动并验证」都走同一条可复现、可审计的流水线——消除「每次配置都不一样、没人知道该看哪份日志、中间件散落各处」的混乱。

**适用**：当需要**启动本项目全部服务并验证通过**时（联调、冒烟、回归前自检、交付给其他 agent 验收）。「验证通过」= **服务全绿 + 浏览器可视化**两条，缺一不可。

**不适用**：纯静态代码审查、不启动服务的单元测试。

---

## 1. 核心原则（七条，不可协商）

1. **应用一律经 IDE MCP 启动** —— 不手敲 `mvn spring-boot:run` / `go run` / `npm run`，不用 Bash 后台常驻。
2. **中间件一律复用 `~/workspace/docker/dev/...(macos)`或`/mnt/e/docker/dev/...(wsl)` 里的既有实例** —— 先 `docker ps` 查运行中容器、再查该目录是否已有 `<中间件>/docker-compose.yml`；**已有（哪怕是他项目起的）直接复用——改本项目配置指向它，不重复起同类型容器**；确无此中间件类型才在该目录补 `<中间件>/docker-compose.yml`。不在项目内私建基础设施。
3. **启动后必看日志** —— IDE 控制台或日志文件；项目**没有日志文件就先补上**，此后一律以文件为准。
4. **有错必究** —— 日志报错导致启动失败，就改配置/代码/数据，重启再验，**直到所有服务启动成功**。
5. **全绿后必开浏览器可视化** —— 服务起来后用 MCP 浏览器工具（`cua` / `playwright` / `cdp` …，择一见附录 E）以**有头模式**打开入口页面、走一条主链路、截图留证；`curl` 返回 200 **不能**替代「页面能开、能看、能点」。
6. **通过后必产出容器化交付** —— 按**标准化分支名**生成项目根 `Dockerfile` 与 `docker/[dev,prd]/[.env,docker-compose.yml]`，镜像名 `<项目名>:<分支名>`（见 §11）；**只产出本地编排不算交付完成**。

> 七条对应「统一化 / 标准化 / 规范化」：**入口统一（IDE MCP）、依赖统一（docker 目录）、证据统一（日志 + 浏览器截图）、闭合标准统一（服务全绿 + 页面可视）、产物统一（本地编排 + 容器化交付）。**

---

## 2. 术语

| 术语 | 定义 |
|---|---|
| 中间件 middleware | 被应用依赖的基础设施：postgres / redis / kafka / minio / centrifugo / livekit … |
| 项目根 | 当前会话工作目录（用户另指则以用户为准） |
| 环境目录 | `~/workspace/docker/dev/...(macos)或 /mnt/e/docker/dev/...(wsl)`（本机所有项目中间件的统一存放处） |
| 服务 service | 「应用」与「中间件」的统称 |
| 验收 DoD | §8 的完成定义检查表 |

---

## 3. 标准流程（九步）

### 步骤 1 · 识别（Recon）
先产出**三张清单**，写进当次汇报：

- **项目根 & 生态** —— 按特征文件判定（附录 A），可多生态共存。
- **应用清单** —— 每个应用的入口、端口、启动方式（run configuration 名）。
- **中间件清单** —— 类型 + 版本 + 端口 + 是否已存在于 `~/workspace/docker/dev/...(macos)或 /mnt/e/docker/dev/...(wsl)`。

```bash
docker ps --format '{{.Names}}\t{{.Ports}}\t{{.Status}}'   # 现有容器与端口
lsof -nP -iTCP:<port> -sTCP:LISTEN                        # 某端口的占用者
```

### 步骤 2 · 中间件就绪
1. **复用优先**：先 `docker ps` 查运行中容器 + 查 `~/workspace/docker/dev/...(macos)或 /mnt/e/docker/dev/...(wsl)` 是否已有该中间件；**已有（哪怕是他项目起的）直接复用**——改本项目配置指向它（端口 / 凭据按实际回写），**绝不重复起同类型容器**。确无此中间件类型时，才按附录 B 模板创建 `<中间件>/docker-compose.yml`（+ 必要配置文件）。
2. 命名与规范统一（§4）。
3. 启动并**逐个健康检查**（不能只看 `docker ps`）：
   ```bash
   # macos
   cd ~/workspace/docker/dev/<中间件> && docker compose up -d
   # wsl
   cd /mnt/e/docker/dev/<中间件> && docker compose up -d
   ```
   健康探针示例见 §4 登记表。

### 步骤 3 · 启动应用（必须经 IDE MCP）
```
mcp__<ide>__get_run_configurations      # 先列出可用 run configuration
mcp__<ide>__execute_run_configuration   # 逐个启动，读返回输出
```
- `<ide>` = `idea` / `goland` / `pycharm`，以当前会话可用的 MCP 为准。
- **没有对应 run configuration → 在 IDE 中创建**，不要退回手敲命令；若确无法走 IDE，须在汇报中显式说明并征得用户同意。

### 步骤 4 · 读日志
1. 先看 **IDE 控制台**（`execute_run_configuration` 返回的 `fullOutputPath`）。
2. 项目**未配置日志文件 → 按 §5 为该生态补上日志文件**，确保「控制台 + 文件」双写。
3. 记录**日志文件的绝对路径**，写进汇报。

### 步骤 5 · 排错（循环直到全绿）
按 §7 手册定位与修复（端口冲突 / 依赖未就绪 / 凭据不符 / schema 漂移 / 缺配置 …），**改完重启再验**，不得跳过任何错误。

> 涉及**删除、改端口、动他项目资源**时，先按 §9 征询用户。

### 步骤 6 · 浏览器可视化（MCP）
服务全绿后，**用真实浏览器验收**（按附录 E 择一工具，**有头模式**）：
1. 打开入口 URL（默认本机 `http://localhost:<port>/`）。
2. 固定视口（如 1440×900），等页面就绪（`networkidle` / 关键元素出现），避免截到半渲染页面。
3. 截图存档 `logs/screenshots/<时间戳>-<页面>.png`，路径写进汇报。
4. 走**一条主链路**（如 登录 → 核心操作 → 结果页），逐步截图。
5. 读**浏览器控制台 + 网络**：有 JS 报错或 4xx/5xx 请求 → 回步骤 5 排错，修完重跑本步。

> 截图是**验收证据**，不是装饰。`curl` 200 只说明端口通了，不说明页面能渲染、能点、能登录。

### 步骤 7 · 验收（DoD）
逐条核对 §8 检查表。验收人可以是人，也可委派独立 agent（见 §8 尾注）。

### 步骤 8 · 产出本地编排
生成 `~/workspace/docker/dev/<项目名>/docker-compose.yml 或 /mnt/e/docker/dev/<项目名>/docker-compose.yml``（目录名 = 项目名，用 `include` 聚合各中间件，见附录 B），并以 `docker compose config` 校验通过。

### 步骤 9 · 容器化交付（验收通过后）
按 §11 产出**可交付镜像与其编排**：
1. 取**标准化分支名** `dev-<semver>-<yymmdd>` / `prd-<semver>-<yymmdd>`（如 `dev-1.0.260910`、`prd-1.0.260910`）。
2. 按生态在**项目根**生成 `Dockerfile`（多阶段构建，模板见 §11.2）。
3. 生成 `docker/dev/` 与 `docker/prd/`，各含 `docker-compose.yml` + `.env`（以及该环境其他必要配置）；镜像名 = `<项目名>:<分支名>`。
4. `.env` **不入库**（`.gitignore` 已含 `.env`），随附 `.env.example` 占位。
5. 逐个校验：`docker compose -f docker/<env>/docker-compose.yml config`。

> 步骤 8 解决「本机怎么跑起来」，步骤 9 解决「别人怎么拿到一个带分支标签的镜像」。**两者产物不同源，不得互相替代。**
> 镜像的 build / push 属发布动作，**执行前按 §9 征得用户同意**；本步骤默认只产出文件与校验，不擅自推送。

---

## 4. 中间件统一规范

> **复用优先（硬性）**：中间件以 `/mnt/e/docker/dev/<中间件>/`（或 `~/workspace/docker/dev/<中间件>/`）为**单一事实来源**，多个项目共用同一份。看到已在运行的容器（如 `dev_redis`、`dev_minio`）就**直接复用**——改本项目配置指向它，**不因项目不同而另起同类型容器**。仅在中间件类型确实缺失时新建一次。

| 维度 | 规范 |
|---|---|
| 目录 | `~/workspace/docker/dev/<中间件>/（macos 或 linx）或 /mnt/e/docker/dev/<中间件>/（wsl）`，内含 `docker-compose.yml`（+ 必要配置，如 `config.json` / `livekit.yaml`） |
| container_name | `<中间件>-dev`（如 `postgres-dev`、`redis-dev`） |
| 端口 | 与项目配置一致（见 §6 端口登记）；冲突即改 |
| 重启策略 | `restart: unless-stopped` |
| 健康检查 | 镜像自带探针则**必配** `healthcheck` |
| 数据 | 持久化（`./data` 绑定或命名卷），`down` 不丢数据 |
| 镜像版本 | 固定到**小版本 tag**（避免 `latest` 漂移），并与项目文档对齐 |

**默认端口登记表**（实际以项目配置为准，此表仅默认值）：

| 中间件 | 默认端口 | 健康检查 |
|---|---|---|
| PostgreSQL | 5432 | `pg_isready` |
| Redis | 6379 | `redis-cli ping` |
| MySQL | 3306 | `mysqladmin ping` |
| Kafka | 9092 | 列举 topics |
| MinIO | 9000 / 9001 | `GET /minio/health/live` |
| Centrifugo | 8000 | HTTP API |
| LiveKit | 7880 / 7881 | HTTP root |

> 新增中间件后，**登记到本表 / 项目文档**，避免端口与版本口口相传。

---

## 5. 日志标准（按生态）

**统一要求**：**控制台 + 文件双写**；文件落在**项目根的 `logs/`**；按**大小 + 日期**滚动；保留有限历史；`.gitignore` 排除（`*.log` / `logs/`）。

| 生态 | 做法 | 文件 |
|---|---|---|
| Java / Spring | `logback-spring.xml`（附录 C 模板） | `logs/<app>.log` |
| Node / Vue | `pino` / `winston`，或构建器日志落盘 | `logs/<app>.log` |
| Go | `zap` / `logrus` + `lumberjack` 轮转 | `logs/<app>.log` |
| Python | `logging` + `RotatingFileHandler` | `logs/<app>.log` |

> 未配置日志文件时，**先看控制台、随后立即补文件配置**——这是本流程的硬性动作，不是可选项。

---

## 6. 端口与冲突规范

**端口来源优先级**：环境变量 → `application.yml` / `.env` → 代码默认值。

**冲突处置流程**：
1. `lsof -nP -iTCP:<port> -sTCP:LISTEN` 找到占用者。
2. 占用者属于**本项目** → 停掉再用。
3. 占用者属于**他项目 / 基础设施**（如 colima 端口转发、他人容器）→ **不改动它**，为本应用改用**空闲端口**。
4. 注意 IPv4 / IPv6 差异占用（某服务仅占 IPv4 时 Tomcat 仍会绑失败）→ 直接换端口，不硬碰。

**端口变更必须三处同步**：① 应用配置；② 客户端 / 页面（baseUrl、回退地址）；③ 本文件或项目文档登记表。

---

## 7. 排错手册（错误 → 处置）

| 症状 | 定位 | 处置 |
|---|---|---|
| `Port x already in use` | `lsof` 占用者 | §6 |
| 连不上 DB / Redis / Kafka | 中间件是否在跑、凭据、端口 | 起中间件 / 改凭据 / 改端口 |
| `column ... does not exist`（schema 漂移） | DB 与 `schema.sql` 对比 | 补列 / 建迁移；**让 schema 幂等自愈** |
| IDE MCP `build_project` 报 `isSuccess:true` 但行为没变 | `target/classes` 里对应 `.class`/资源文件的 mtime、或 grep 新符号 | 外部工具（agent 的 patch/python）改过源码后，**必须 `build_project` 带 `rebuild:true`**：不带 rebuild 的增量构建看不到 IDE 之外的改动，会"成功但什么都没编译"（假绿）。核对 mtime/grep 后重启应用再验 |
| 改完代码重启才生效 | 应用进程还跑着旧 class | 先 `netstat -ano \| grep <port>` 找 PID → `MSYS_NO_PATHCONV=1 taskkill /PID <pid> /F`，再经 IDE MCP 重新 `execute_run_configuration`（端口占用时 Spring 会直接启失败，日志里是 `Port 8083 was already in use`） |
| 登录 401 / 凭据不符 | 文档 vs 实际（DB） | 以**实际**为准回写文档（账号、密码、端口） |
| 无 run configuration | `get_run_configurations` | 在 IDE 补配置 |
| 日志无输出 | 无日志文件配置 | §5 补日志 |
| 起后端点 404 | 路由 / 上下文路径 | 核对映射与 `context-path` |
| 页面白屏 / 卡在 loading | 浏览器控制台 | 修前端报错 / 补后端接口 |
| 浏览器 Network 出现 4xx / 5xx | 失败请求的 URL 与响应 | 对照本表前几行定位（端口 / 凭据 / schema / 路由） |
| 登录后立刻跳回登录页 | 浏览器控制台 + 响应头 | token / CORS / cookie 域，按实际回写配置 |
| 浏览器 MCP 无可用工具 | 当前会话工具列表 | 按附录 E 降级（`webapp-testing` → Chrome headless）并说明 |

> **治本原则**：能幂等的就幂等（`create table if not exists`、`add column if not exists`），杜绝「只有全新环境才对」的隐性依赖。

---

## 8. 验收标准（Definition of Done）

- [ ] **中间件**：全部 `Up`（healthy），健康探针通过
- [ ] **应用**：全部进程存活，经 IDE run configuration 正常启动、无异常退出
- [ ] **端点**：关键健康端点返回 200（如 `/actuator/health`）
- [ ] **日志**：排错后**无 ERROR / Exception**
- [ ] **入口**：页面 / 主入口经**真实浏览器**（MCP，有头模式）打开可访问，截图留证（附录 E）
- [ ] **控制台 / 网络**：浏览器无 JS 报错、无 4xx / 5xx 请求
- [ ] **主链路**：至少一条端到端业务链路在浏览器中跑通（如 登录 → 核心操作），逐步截图存 `logs/screenshots/`
- [ ] **产出（容器化交付）**：项目根 `Dockerfile` 与 `docker/[dev,prd]/[.env,docker-compose.yml]` 就位，镜像名 = `<项目名>:<分支名>`，各环境 `docker compose config` 校验通过

**验收方式**：现阶段人工核对本表；成熟后委派**独立 agent** 复核——只读、按表打勾、问题分级回报，不静默跳过。**浏览器三条（入口 / 控制台网络 / 主链路）以截图文件为凭据，拿不出截图即视为未通过。**

---

## 9. 边界与禁止（安全红线）

- **不杀他项目**的容器 / 进程；确需释放其占用端口，**先报告并征得用户同意**。
- **不硬编码密钥**；新增凭据放本地配置（`.gitignore` 覆盖），不入库。
- **不动共享中间件的数据卷**，避免误删他人数据。
- `docker compose down` **只作用于本项目的 compose 文件**。
- 破坏性 / 不可逆操作前**先确认**。

---

## 10. 产出物清单

| 产出 | 路径 |
|---|---|
| 中间件定义 | `~/workspace/docker/dev/<中间件>/docker-compose.yml(macos或linux) ,/mnt/e/docker/dev/<中间件>/docker-compose.yml（wsl）` |
| 应用镜像定义 | 项目根 `Dockerfile` |
| 交付编排 | 项目根 `docker/dev/docker-compose.yml` · `docker/prd/docker-compose.yml` |
| 交付环境变量 | 项目根 `docker/[dev,prd]/.env`（**不入库**）+ `.env.example` |
| 日志文件 | 项目根 `logs/<app>.log` |
| 页面截图 | 项目根 `screenshots/<时间戳>-<页面>.png` |
| 日志配置 | 按生态（§5） |

---

## 11. 容器化交付（Dockerfile + `docker/[dev,prd]/`）

**目的**：把「本机能跑」变成**可交付镜像**——镜像 tag 绑定标准化分支名，环境差异全部收敛进 `.env`，同一套 compose 换 `.env` 即可切 dev / prd。

**11.1 命名规范**

| 维度 | 规范 |
|---|---|
| 分支名 | `<env>.<semver>.<yymmdd>`，`env ∈ {dev, prd}`；例 `dev.1.0.260910`、`prd.1.0.260910` |
| 镜像名 | `<项目名>:<分支名>`；例 `nebula-im:dev.1.0.260910` |
| 目录 | 项目根 `docker/<env>/`，内含 `docker-compose.yml` + `.env`（+ 入库的 `.env.example`，以及该环境其他必要配置） |
| Dockerfile | 项目根 `Dockerfile`，**多阶段构建**：builder 阶段编译，运行阶段只留产物 |
| 环境差异 | 端口 / 凭据 / 中间件地址 / 副本数一律走 `.env`，**不写死进 Dockerfile** |
| 构建上下文 | 项目根；`.dockerignore` 排除 `target/`、`node_modules/`、`logs/`、`.git/` |

**11.2 Dockerfile 模板（按生态择一，落项目根）**

Java / Spring（Maven）：
```dockerfile
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /build
COPY pom.xml .
RUN mvn -B -q dependency:go-offline
COPY src ./src
RUN mvn -B -q clean package -DskipTests

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /build/target/*.jar app.jar
EXPOSE 8083
ENTRYPOINT ["java","-XX:MaxRAMPercentage=75","-jar","app.jar"]
```

Go：
```dockerfile
FROM golang:1.22-alpine AS build
WORKDIR /build
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/app ./cmd/...

FROM gcr.io/distroless/static-debian12
COPY --from=build /out/app /app
EXPOSE 8081
ENTRYPOINT ["/app"]
```

前端 Vue / Vite（Nginx 托管静态产物）：
```dockerfile
FROM node:22-alpine AS build
WORKDIR /build
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /build/dist /usr/share/nginx/html
EXPOSE 80
```

> 其余生态同理（builder 编译 + 精简 runtime）；**运行阶段不装构建工具链**。

**11.3 `docker/<env>/docker-compose.yml`**

```yaml
# <项目名> <env> 环境交付编排。应用镜像由 CI / 本地按 <分支名> 构建。
services:
  <app>:
    image: <项目名>:${IMAGE_TAG}
    container_name: <app>-${ENV}
    restart: unless-stopped
    ports:
      - "${HOST_PORT}:${CONTAINER_PORT}"
    env_file:
      - .env
    environment:
      SPRING_PROFILES_ACTIVE: ${ENV}
      DB_URL: ${DB_URL}
      REDIS_HOST: ${REDIS_HOST}
      KAFKA_BROKERS: ${KAFKA_BROKERS}
```

> 中间件（postgres / redis / kafka …）**不在此文件内重定义**：交付环境用托管服务或 §4 那套 `dev` 编排，此处只描述**应用容器**，避免出现第二份基础设施真源。

**11.4 `docker/<env>/.env.example`（`.env` 由它复制，`.env` 本身不入库）**

```dotenv
ENV=dev
IMAGE_TAG=dev.1.0.260910
HOST_PORT=8083
CONTAINER_PORT=8083
DB_URL=jdbc:postgresql://postgres-dev:5432/nebula
REDIS_HOST=redis-dev
KAFKA_BROKERS=kafka-dev:9092
```

**11.5 校验与红线**

- 交付前**逐个环境**执行 `docker compose -f docker/<env>/docker-compose.yml config`，必须通过。
- `IMAGE_TAG` 必须等于分支名，**禁用 `latest`**。
- `.env` **不入库**（`.gitignore` 已含 `.env`）；密钥只进 `.env`，不进 Dockerfile / compose 明文字段。
- 镜像 build / push 属发布动作，**先确认再执行**（§9）；本步骤默认只产出文件与校验，不擅自推送。

---

## 附录 A · 生态探测

| 生态 | 特征文件 |
|---|---|
| 前端 JS / TS | `package.json` / `yarn.lock` / `pnpm-lock.yaml` / `vite.config.*` / `next.config.*` |
| Java | `pom.xml` / `build.gradle` / `build.gradle.kts` / `settings.gradle` |
| Go | `go.mod` / `go.sum` |
| Python | `requirements.txt` / `pyproject.toml` / `setup.py` / `Pipfile` |

可多生态共存（Java 后端 + 前端子目录），逐个子目录判定。

---

## 附录 B · 模板

**B1 单个中间件 `docker-compose.yml`**
```yaml
services:
  <middleware>:
    image: <image>:<pinned-tag>
    container_name: <middleware>-dev
    restart: unless-stopped
    ports:
      - "<host_port>:<container_port>"
    environment:
      <KEY>: <VALUE>
    volumes:
      - <data_volume>:/var/lib/<middleware>
    healthcheck:
      test: ["CMD-SHELL", "<probe>"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s
volumes:
  <data_volume>:
```

**B2 项目级 `docker-compose.yml`（聚合）**
```yaml
# <项目名> 本地中间件总编排。应用由 IDE 启动，不在此列。
# 每个中间件定义在 ../<中间件>/docker-compose.yml，此处只做聚合（单一事实来源）。
include:
  - ../postgresql/docker-compose.yml
  - ../redis/docker-compose.yml
  # …本项目所需的其余中间件
```

---

## 附录 C · Java 日志模板（`logback-spring.xml`）
```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <property name="LOG_DIR" value="${LOG_DIR:-logs}"/>
    <property name="LOG_PATTERN"
              value="%d{yyyy-MM-dd HH:mm:ss.SSS} %-5level [%thread] %logger{36} - %msg%n"/>

    <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder><pattern>${LOG_PATTERN}</pattern><charset>UTF-8</charset></encoder>
    </appender>

    <appender name="FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">
        <file>${LOG_DIR}/<app>.log</file>
        <rollingPolicy class="ch.qos.logback.core.rolling.SizeAndTimeBasedRollingPolicy">
            <fileNamePattern>${LOG_DIR}/<app>.%d{yyyy-MM-dd}.%i.log.gz</fileNamePattern>
            <maxFileSize>50MB</maxFileSize>
            <maxHistory>14</maxHistory>
            <totalSizeCap>1GB</totalSizeCap>
        </rollingPolicy>
        <encoder><pattern>${LOG_PATTERN}</pattern><charset>UTF-8</charset></encoder>
    </appender>

    <root level="INFO">
        <appender-ref ref="CONSOLE"/>
        <appender-ref ref="FILE"/>
    </root>
</configuration>
```

---

## 附录 D · IDE MCP 速查

| 动作 | 工具 |
|---|---|
| 列出 run configuration | `mcp__idea__get_run_configurations` / `mcp__goland__get_run_configurations` |
| 启动（后台，读输出） | `mcp__idea__execute_run_configuration` / `mcp__goland__execute_run_configuration` |
| 读启动输出 | 上述返回的 `fullOutputPath` |
| 构建校验 | `mcp__idea__build_project` |

> **浏览器类 MCP（cua / playwright / cdp …）见附录 E** —— 起完应用后的可视化验收走那一份。

---

## 附录 E · 浏览器可视化（MCP）

**目的**：把「页面真的能开、能看、能点、能登录」变成**可留证的机器动作**——这是 `curl` / 日志都覆盖不到的一层。

**择一优先级**（可用即用；**先枚举当前会话实际可用的浏览器工具再调用，不要猜工具名**）：

| 优先级 | 工具 | 什么时候选它 | 备注 |
|---|---|---|---|
| 1 | `cua`（computer-use） | 要看**整个桌面 / 多窗口 / 原生弹窗 / 非 Web 客户端** | 覆盖面最广，可接管真实鼠标键盘 |
| 2 | `playwright` | 要**确定性交互**：点击、填表、等待、断言 | 做「主链路」步骤化验证的首选 |
| 3 | `cdp` / `chrome-devtools-mcp` | 要抓**控制台报错 / 网络请求 / 性能** | 本机已装 Chrome：`C:\Program Files\Google\Chrome\Application\chrome.exe` |
| 4 | 内置 `webapp-testing` skill | 上述 MCP 都未配置时的**兜底** | 本工作区自带，Playwright 工具包 |
| 5 | `chrome --headless=new --screenshot` | 最简兜底（**只能截图，不能交互**） | `chrome.exe --headless=new --screenshot=out.png --window-size=1440,900 <url>` |

> MCP 工具命名形如 `mcp__<server>__<tool>`。某个 server 不在线就沿上表**降级**，并在汇报里写明最终用了哪一档。

**可视化 = 有头模式（headed）**：默认**不得**用 headless —— 「可视化」的意义就是让人/agent 真看到界面在动。确无显示环境必须 headless 时，在汇报中写明理由。

**标准动作**：
1. `navigate` / `open` 入口 URL（默认 `http://localhost:<port>/`）。
2. 固定视口（1440×900），等就绪（`networkidle` 或关键元素出现）——避免截到半渲染页面。
3. `screenshot` → `logs/screenshots/<yyyyMMdd-HHmmss>-<页面名>.png`。
4. 主链路逐步操作 + 逐步截图（登录 → 核心操作 → 结果页）。
5. 取**控制台消息**与**失败请求**；两者任一异常都算**没通过**。
6. 异常 → 回 §3 步骤 5 排错 → 修完重跑本步。

**证据与红线**：
- 截图是**验收证据**，路径与结论必须写进汇报；**拿不出截图即视为未验收**。
- 截图 / 录像前**遮蔽敏感信息**（密码、token、身份证、手机号），必要时只截局部。
- 只操作**本项目**的页面；不点他项目的后台，不做破坏性写操作（下单、删除、群发…）。

**与 §5 的关系**：浏览器控制台报错与失败请求是排错手册的**一等输入**——比后端日志更早暴露前端与接口契约问题。

---

## 附录 F · 一页速记（TL;DR）

> **先 Recon（含 `docker ps` 盘点已有中间件）→ **复用已有**中间件（缺才在 `~/workspace/docker/dev/` 补）→ 经 IDE MCP 起应用 → 看日志（缺则补文件）→ 有错就改到全绿 → MCP 浏览器（有头）打开页面 + 走主链路 + 截图 → 过 §8 DoD → 产出 `<项目名>/docker-compose.yml` → 按分支名产出 `Dockerfile` + `docker/[dev,prd]/` 并校验。**
