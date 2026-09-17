# aap-server · TDD 状态（真源，随每轮任务追加）

> 任务清单与 DoD：`docs/backend/03-任务与TDD计划.md`；接口↔任务映射台账：`.agents/state/aap-server-feature-status.csv`
> 红绿证据：`.agents/state/evidence/red-Txx.txt` / `green-Txx.txt`
> 环境事实（实测）：JDK 25.0.4 · Maven 3.8.6（本机 `mvn` 脚本坏 → 用 `~/bin/mvn` 包装器直启 classworlds）
> · PostgreSQL 18.6（复用 `dev_postgres`，库 `aap_server_dev` / `aap_server_test`）· Spring Boot 4.1.1 · MyBatis-Flex 1.11.8
> · 私服 BOM `com.hioas.framework:hioas-dependencies:1.0.0-SNAPSHOT` 403 不可解析（偏差 D-BUILD-01）
> · 密钥统一放 `E:\env\aap-server.env`，用 `tools/with-env.sh aap-server <命令>` 载入
> · Spring Boot 4 = Jackson 3（`tools.jackson`），测试侧契约校验用 networknt（内部 Jackson 2），两者不交叉

---

## 轮次记录

### R01 · T01 工程骨架与统一契约 —— ✅ 完成

- 红：`mvn -B -ntp test` → 编译失败（`ApiEnvelope`/`ErrorCode`/`ApiException` 不存在）→ 证据 `evidence/red-T01.txt`
- 绿：`Tests run: 16, Failures: 0, Errors: 0` ×2 轮 → `evidence/green-T01.txt`、`evidence/green-T01-run2.txt`
- 关键结论
  - Spring Boot 4.1.1 的 `spring-boot-starter-test` **不含** `@AutoConfigureMockMvc`（迁到 `spring-boot-webmvc-test`）
    → 集成测试改用**真实 HTTP**（`@LocalServerPort` + `java.net.http.HttpClient`），更贴近客户端线格式，契约测试才有意义
  - Spring Boot 4 默认 **Jackson 3**：`com.fasterxml.jackson.databind` 不在主 classpath；
    `spring.jackson.serialization.*` 旧枚举（如 `write-dates-as-timestamps`）会导致**启动失败** → 已移除
  - log4j2 pattern 的 `%X{traceId:-}` 默认值语法不生效（渲染为空），改 `%X{traceId}`
  - `@SpringBootApplication(exclude = UserDetailsServiceAutoConfiguration.class)` 去掉随机密码噪音
- 交付：`ApiEnvelope` / `ErrorCode`(28 码) / `ApiException` / `GlobalExceptionHandler` / `TraceIdFilter` /
  `PageResult` / `PageQuery` / `SecurityConfig` / `log4j2-spring.xml` / `application.yml`
- 契约测试：真实响应体经 `docs/backend/json-schema/common/*.schema.json` 校验；错误码枚举与 schema 逐条一致

### R02 · T02 数据库迁移与持久层底座 —— ✅ 完成

- 红：`evidence/red-T02.txt`（迁移首次执行失败：`column "version" specified more than once`）
- 绿：`Tests run: 26, Failures: 0, Errors: 0` ×2 轮 → `evidence/green-T02.txt`、`green-T02-run2.txt`
- 关键结论
  - `aap_detection_baseline` 的基线版本号列改名 `baseline_version`（与审计乐观锁列 `version` 撞名，PG 报 42701）
  - 幂等 DDL 全量 `create table/index if not exists`，Flyway 重跑 `migrationsExecuted=0`（幂等自愈）
  - 表清单断言必须排除分区子表，且分区父表 `relkind='p'`（只查 `'r'` 会漏掉 `aap_usage_hourly`）
  - MyBatis-Flex 乐观锁：过期 `version` 的更新影响 0 行（**不覆盖**），重新取数后正常递增
  - jsonb 列用自研 `JsonbTypeHandler`（`Types.OTHER` 写参数），不引入 PGobject 编译依赖、不依赖 Jackson2 版 handler
  - 密钥入 `E:\env\aap-server.env`：`application.yml` 只留 `${DB_PASSWORD}` / `${AAP_JWT_SECRET}` /
    `${AAP_CREDENTIAL_AES_KEY}` 占位，缺失即启动失败（不静默用默认值）
- 交付：`V1__baseline.sql`（54 表 + 分区 + 唯一索引 + 字典数据）/ `BaseEntity` / `AuditContext` /
  `AuditListeners` / `JsonbTypeHandler` / `JsonCodec` / `ProviderEntity` / `ProviderMapper`
- 证据：`MigrationTest`（54 表/幂等/关键唯一索引/分区/审计列）、`PersistenceBaseTest`（雪花 ID/审计填充/逻辑删除/乐观锁/分页）

---

## 未决与下一步

- 下一轮：**R03 · T03 账号接入**（AUTH-01…06，AC-01…05）——JWT 签发与校验、手机号密文+hash+mask、
  验证码 300s/60s 频控/5 次锁 15 分钟、微信登录、`/auth/me`（含设置页字段）；同时把 `SecurityConfig`
  收紧为 `anyRequest().authenticated()` + 角色规则。
- 待办（跨轮）：`logs/` 与 `target/` 不得入库（检查 `.gitignore`）；`aap-server/README.md` 待补运行说明。
