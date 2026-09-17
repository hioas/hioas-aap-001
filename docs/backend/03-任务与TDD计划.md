# 任务与 TDD 计划（aap-server）

> 执行方式：**TDD 强制**（先红后绿、连跑两轮全绿）——SKILL `.agents/skills/dev/SKILL.md` §2.1。
> 每个任务：① 写会红的测试 → ② 留红基线输出到 `.agents/state/evidence/red-<任务号>.txt` → ③ 实现 → ④ `mvn test` 绿 → ⑤ 回写台账与状态文件 → ⑥ 单独提交。
> 验收用例（AC-xx）来自 `.calicat/prd/21-验收标准.md`；接口 ID 来自 `02-API接口模型清单.md`。

## 0. 环境事实（实测）

| 项 | 实测值 |
|---|---|
| JDK | Temurin 25.0.4（`E:\workspaces\jdk\temurin-25.0.4`） |
| Maven | 本机 `bin/mvn`（PATH 上的 3.8.6）坏 → 用 `~/bin/mvn` 包装器（直启 classworlds） |
| 本地仓库 | `E:/workspaces/maven/repository`（`settings.xml` 指定） |
| Spring Boot | 4.1.1 已在本地仓库 |
| MyBatis-Flex | 1.11.8（`mybatis-flex-spring-boot4-starter`）可从阿里云拉取 |
| PostgreSQL | `dev_postgres`（postgres:18.6，`localhost:5432`）**复用不另起容器**；凭据来自 `E:\env\aap-server.env`（不入库） |
| 私有 BOM | `com.hioas.framework:hioas-dependencies:1.0.0-SNAPSHOT` → 403 不可解析（D-BUILD-01） |

测试库：`aap_server_test`（由 `TestDatabaseInitializer` 首次运行时创建，Flyway 迁移 + 每轮清表）；
开发库：`aap_server_dev`。

## 1. 任务分解

| 任务 | 名称 | 覆盖接口 | 覆盖 AC | 关键交付 | 依赖 |
|---|---|---|---|---|---|
| **T01** | 工程骨架与统一契约 | — | — | POM/配置/log4j2 双写、`ApiEnvelope`/`ApiError`/`ErrorCode`、traceId 过滤器、全局异常处理、`/actuator/health`、契约测试骨架 | — |
| **T02** | 数据库迁移与持久层底座 | — | — | Flyway `V1__baseline.sql`（54 表幂等 DDL）、MyBatis-Flex 配置（分页/逻辑删除/乐观锁/雪花 ID/审计填充） | T01 |
| **T03** | 账号接入 | AUTH-01…06 | AC-01…05 | JWT 签发/校验、手机号密文+hash+mask、验证码 300s/60s 频控/5 次锁、微信登录、`me`（含设置页字段） | T02 |
| **T04** | 供应商档案与资质 | PROV-01…05 | AC-06 | 12 态状态机校验、uscc 唯一、`manual_override`→理由必填（R-47a）、`Idempotency-Key` 重放、`If-Match`、完整度计算 | T03 |
| **T05** | 测试凭证 | CRED-01…07 | AC-07…13、AC-29/30/48 | AES-256-GCM(`base64(iv‖ct‖tag)`) 落库、指纹 SHA-256 唯一、`sk-****abcd` 脱敏、base_url 规范化、SSRF 校验、预检、明文 reveal + 审计 | T04 |
| **T06** | 检测引擎接入 | DET-01…06 | AC-13…17、AC-19/20/47 | 任务状态机、C2 互斥（E-1301）、日配额 5 次、D1–D8 打分子项（纯函数）+ 权重归一化 + 四分支判定 + D7 否决、`detection_status` 派生 | T05 |
| **T07** | 检测报告 | RPT-01…04 | AC-18/21/49 | 报告 1:1 任务、四段式解释、免责声明与「禁正品」措辞校验、/html、/export、复测触发 | T06 |
| **T08** | 报价单与定价 | QT-01…11 | AC-22…25 | 报价单状态机、门槛 E-1602、明细行唯一、时段/阶梯/倍率校验（E-1401/1402/1403/1404）、版本快照、提交/撤回 | T07 |
| **T09** | 计费编译与三道闸门 | QT-12、ADM-Q01、ADM-CP01…04 | AC-26/27/28/33 | 编译器（len 分档/峰谷/组合/请求级/`v1: `前哨）、C1–C10 逐字节用例、V1–V6 模拟校验、`source_hash` 幂等、未确认禁写 E-1407 | T08 |
| **T10** | 运营审核 | ADM-R01…05 | AC-31/32 | 领取乐观锁、驳回必填原因+定位字段、通过→自动生成合同→`CONTRACT_PENDING` | T09 |
| **T11** | 合同 / 打款 / 结算 | CON-01…04、PAY-01、ADM-CT01…03、ADM-PAY01…03 | AC-39/40/41 | 合同状态机、未签署禁打款 E-1701、打款仅记录、上架 `PUBLISHED` | T10 |
| **T12** | 用量聚合与对账 | USE-01/02、ADM-U01/02 | AC-43…46 | 小时桶 UPSERT 幂等、缓存字段解析三态、对账指标（差异率 ±5%）、E-1801 降级、`/usage/summary` 超集响应 | T06 |
| **T13** | 站内信 / 审计 / 设置 | NTF-01/02、ADM-A01 | AC-21/48 | 站内信列表与已读、审计查询（四类操作含 before/after）、未读数 | T03 |
| **T14** | new-api 同步与配置 | ADM-S01…06、ADM-P01…03、ADM-C01/02、ADM-Q02、ADM-CFG01…10 | AC-34/35/36/42/50 | 渠道绑定命名 `AAP-{short}-{seq}`、幂等键、退避重试 ≤5（30s/2m/8m/30m/2h）、回读一致性、mock 适配器、检测配置/报告模板版本发布 | T09,T12 |
| **T15** | 端到端验收与交付 | 全部 | 主链路 | 起服务 + `aap-client` 联调（浏览器截图）+ `Dockerfile` + `docker/[dev,prd]` + 台账收口 | 全部 |

## 2. 每任务 DoD（缺一不可）

1. 测试先红：新增测试在未实现时报预期失败，原始输出存 `.agents/state/evidence/red-<任务号>.txt`。
2. 全绿：`mvn test` 通过；**连跑两轮**结果一致（第二轮无偶发红）。
3. 契约校验：涉及响应的测试用 `docs/backend/json-schema/**` 校验真实响应体（`SchemaAssert`）。
4. 无 ERROR：`logs/aap-server.log` 中排错后无 ERROR/Exception。
5. 台账回写：`.agents/state/aap-server-feature-status.csv` 对应行状态 → `已实现`；状态文件追加一轮记录。
6. 单独提交：`feat(aap-server): Txx <范围> <做了什么>`。

## 3. 测试分层

| 层 | 技术 | 覆盖对象 | 运行成本 |
|---|---|---|---|
| 单元 | JUnit 5 + AssertJ（无 Spring） | 打分公式、编译器、校验器、加密/脱敏、状态机、退避计算 | 毫秒级 |
| 集成 | `@SpringBootTest` + MockMvc + 真实 PG（`aap_server_test`） | Controller→Service→Mapper→DB 全链路、事务/约束/幂等 | 秒级 |
| 契约 | JSON Schema 校验器（networknt） | 每个接口响应体符合 `docs/backend/json-schema/**` | 随集成测试 |
| 验收 | `curl` + 浏览器（MCP，有头） | 主链路端到端 | T15 |

## 4. 红绿证据位置

```
.agents/state/evidence/
├── red-T01.txt … red-T15.txt      # 红基线（未实现时的失败输出）
├── green-T01.txt … green-T15.txt  # 绿结果（mvn test 摘要，含用例数）
└── contract-<接口ID>.json          # 契约测试抓取的真实响应样本
```

## 5. 状态与台账

- 台账：`.agents/state/aap-server-feature-status.csv`（列：任务号/接口ID/方法/路径/依据/状态/证据/提交）
- 状态：`.agents/state/aap-server-tdd-state.md`（每轮：命令、结果、红绿、未决）

## 6. 变更记录

- 2026-09-17 首版：依据 `00-设计总览.md`/`01-ER数据模型.md`/`02-API接口模型清单.md` 制定。
