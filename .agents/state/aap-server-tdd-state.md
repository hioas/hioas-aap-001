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

### R03 · T03 账号接入（AUTH-01…06 / AC-01…05）—— ✅ 完成

- 红：`evidence/red-T03.txt`（9 例全红：接口不存在）
- 绿：`evidence/green-T03.txt`（`Tests run: 35, Failures: 0`）
- 关键结论（踩坑与修正）
  1. **验证码锁定必须独立事务**：`AuthService.smsLogin` 有外层事务，若把「错误次数 + 锁定时间」写在同事务里，
     抛业务异常会把它们一起回滚 → AC-04 永不生效（实测第 6 次仍登录成功）。
     修正：拆出 `SmsAttemptRecorder`，用 `@Transactional(REQUIRES_NEW)` 先落库再抛异常。
  2. `JwtAuthenticationFilter` **不要加 `@Component`**：否则被 Spring Boot 当 Servlet Filter 自动注册，
     与安全链里的注册重复执行两次；改为在 `SecurityConfig` 里以 Bean 形式装入安全链。
  3. 测试专用路径放行：`support/TestSecurityConfig`（`securityMatcher("/api/v1/__test/**")`，最高优先级链），
     让 T01 的契约探针在安全链收紧后仍可用，且不动生产放行清单。
  4. 测试环境验证码回读：`app.sms.expose-code=true`（**生产默认 false**，仅测试 profile 打开）——
     端到端验收需要真实走通登录，而短信网关不接真实通道。
- 交付：`ProviderAccountEntity/SmsCodeEntity/AuthTokenEntity` + Mapper、`JwtService`、`SmsService`、
  `SmsAttemptRecorder`、`AuthService`、`AuthController`、`JwtAuthenticationFilter`、`AuthPrincipal`、
  `WechatClient`（确定性桩，未接入微信凭据）、`CryptoService`、`DocNoGenerator`、`AuditService`/`AuditLogEntity`、
  `AppProperties`、`SecretStartupCheck`、`V2__sequences.sql`
- 附加修正：**V1 基线补齐 34 张表的 `created_by/updated_by`**（ER 文档 §1 承诺「审计字段业务表通用」，
  原 DDL 漏列；基线尚未发布，直接修 V1 并重置测试库 schema，未走 V3 补丁）

### R04 · T04 供应商档案与资质（PROV-01…05 / AC-06）—— ✅ 完成

- 红：`evidence/red-T04.txt`（接口不存在 → 404）
- 绿：`evidence/green-T04.txt`（`Tests run: 44, Failures: 0`）
- 关键结论
  1. **幂等必须用过滤器而非拦截器**：Spring Security 的 `HeaderWriterFilter` 会在 MVC 前再包一层响应，
     `HandlerInterceptor` 里 `response instanceof ContentCachingResponseWrapper` 恒为 false，
     幂等记录永远停在 `IN_PROGRESS`、第二次请求照旧重复执行（实测复现）。
  2. **`ContentCachingRequestWrapper` 只缓存不回放**：过滤器读完请求体算哈希后，下游控制器读到空体 → E-1001。
     自研 `CachedBodyRequestWrapper` 把字节回放给下游。
  3. `jsonb` 列会规范化键序与空白 → 幂等重放**语义相等但非逐字节相同**；断言改为 JSON 语义比较 + traceId 一致。
  4. Spring 7 里 `ContentCachingRequestWrapper` 只有双参构造；`copyBodyToResponse()` 要保留**具体类型**才可见。
- 交付：`ProviderService`/`ProviderController`/`ProviderProfileResponse`、`QualificationEntity`+Mapper、
  `IdempotencyFilter` + `CachedBodyRequestWrapper` + `IdempotencyRecordEntity/Mapper`、`CachingWrapperFilter`
- 规则落地：uscc 全局唯一（E-1104）、手机号密文+hash+mask（R-48）、`manual_override` 必填理由（R-47a）、
  `If-Match` 过期写拒绝（E-1601）、资质扩展名白名单 + ≤10MB、完整度服务端唯一口径

---

## 未决与下一步

- 下一轮：**R05 · T05 测试凭证**（CRED-01…07，AC-07…13、AC-29/30/48）——AES-256-GCM 落库、指纹唯一、
  `sk-****abcd` 脱敏、base_url 规范化、SSRF 出站防护、预检、明文 reveal（仅超管 + 二次验证 + 审计）。
- 待办（跨轮）：`aap-server/README.md` 运行说明；T15 时把 `aap-client` 的 `baseUrl` 指向本服务做联调截图。
