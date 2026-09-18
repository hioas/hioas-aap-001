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
- 绿：`Tests run: 16, Failures: 0, Errors: 0` → `evidence/green-T01.txt`
- ⚠️ **证据更正（R08 复核）**：曾名为 `green-T01-run2.txt` 的文件里其实是 `Errors: 10`（**不是绿**），已重命名为 `evidence/T01-run2-concurrent-dirty.txt` 并撤回「连跑两轮全绿」的宣称。成因见下文「并发跑测试」结论，非产品缺陷。
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
- 绿：`Tests run: 26, Failures: 0, Errors: 0` ×2 轮 → `evidence/green-T02.txt`、`green-T02-run2.txt`（两个文件均已复核：末行汇总均为 `Failures: 0, Errors: 0`）
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
- ⚠️ **证据更正（R08 复核）**：曾名为 `green-T03-run2.txt` 的文件里是 `Tests run: 44, Failures: 8`（当时 T03/T04 两套用例被**并发**跑在同一套测试库上，`truncateAll()` 互相清表 → 随机失败），已重命名为 `evidence/T03-run2-concurrent-dirty.txt`；T04 的干净第二轮是 `green-T04-run2.txt`（44/44 绿）。
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

### R05 · T05 测试凭证（CRED-01…07 / AC-07…13、AC-29/30/48）—— ✅ 完成

- 红：`evidence/T05-run1.txt`（编译失败）→ `T05-run2..4.txt`（逐轮修正 4 类缺陷）
- 绿：`evidence/green-T05.txt`（`Tests run: 61, Failures: 0`）
- 关键结论
  1. **JSON Schema 外部 $ref 的两种坏法**（契约测试踩全了）：
     给模型写 `$id: https://...` → 相对 `$ref` 被解析成绝对地址去联网拉取（`Failed to load json schema from https://`）；
     用 InputStream 装载 → `URI is not absolute`。正解：**不写 $id** + 用**文件 URI** 装载（`getSchema(file.toUri())`）。
  2. **`@PreAuthorize` 失败不会走安全链的 accessDeniedHandler**：它由 MVC 抛出，
     会被 `@ExceptionHandler(Exception.class)` 吞成 500 E-2001。必须显式处理
     `AccessDeniedException`（403 E-1901）与 `AuthenticationException`（401 E-1902）。
  3. **IPv6 字面量**：`URI.getHost()` 返回带方括号的 `[::1]`，直接丢给 `InetAddress.getAllByName` 会解析失败，
     被「解析不了就放行」的兜底策略误放行。必须先剥方括号。
  4. 环回地址的拒绝无法在 HTTP 用例里验证（测试 profile 为跑本地上游桩开了 `allow-loopback`）→
     单独用 `OutboundUrlGuardTest` 在**生产配置**下断言环回被拒（AC-29 全覆盖），HTTP 用例覆盖其余网段。
  5. 预检失败/成功都要落库 → 复用 T03 的教训：拆 `CredentialPrecheckRecorder`（REQUIRES_NEW），
     失败先落库再抛 E-1101，成功则「凭证 ACTIVE + 任务入队」同事务。
- 交付：`CredentialEntity/PrecheckEntity` + Mapper、`CredentialService/Controller/Views`、
  `OutboundUrlGuard`（SSRF）、`UpstreamProbe`（401/403 不重试、5xx/网络错误 ≤2 次）、
  `CredentialPrecheckRecorder`、`DetectionJobEntity`（C2 载体）、`AdminUserEntity`、`V3__admin_phone.sql`、
  `GlobalExceptionHandler` 补安全异常分支、`SchemaAssert` 修正装载方式

### R06 · T06 检测引擎接入（DET-01…06 / AC-13…17、AC-19/20/47）—— ✅ 完成

- 红：`evidence/T06-run1.txt`（9 例 HTTP + 13 例纯函数，5 条红）→ 逐条修正后
- 绿：`evidence/green-T06.txt`（`Tests run: 83, Failures: 0`）
- 关键结论
  1. **算术必须复核**：D7 五项加权（0.15/0.25/0.35/0.15/0.10）手算成 78.5，实际 78.0；
     总分 (64.8/0.9)=72.00 也被我算错成 70.53。测试期望值是**用计算器复核后**改的，不是把实现改成迁就错误期望。
  2. `weight_used` 只有在 `summarize()` 归一化后才算得出 → 落库必须取**汇总后的权重**，
     否则报告里显示 0 而总分却用了权重（口径不一致的经典坑）。
  3. 人工放行（AC-20）的语义是「人工介入跳过自动流程」→ 除 `CANCELLED` 外都应允许，
     不该按"仅终态可放行"收紧（否则运营在排队/进行中想放行会被 E-1601 挡住）。
  4. 任务状态机新增 `CANCELLED`（17-spec §4 未列，15-数据模型 §4.4 有）→ 记偏差 D-STATE-01，以数据字典为准。
- 交付：`ProbeScoring`（D1–D8 纯函数 + 权重归一化 + 四分支判定 + 置信度 + 措辞）、`DetectionJobEntity/ResultEntity`
  + Mapper、`DetectionService`（建/查/取消/放行/引擎回写闭环）、`DetectionController`、`DetectionViews`

### R07 · T07 检测报告（RPT-01…04 / AC-18、AC-21、AC-49）—— ✅ 完成

- 红：`evidence/T07-run1.txt`（5 例中 2 例红）→ 4 轮迭代 → 绿：`evidence/green-T07.txt`（`Tests run: 90, Failures: 0`）
- **本轮抓到的真实缺陷与契约错误（值得记住）**
  1. **分页字段名错了**：客户端读 `raw.items`（`credentials-model.ts:140`、`detecting-model.ts:212`），
     而 `PageResult` 与设计文档（`docs/api/接口字段级schema.md:21`）都写 `list`。若上生产，**所有列表页都会空白**。
     已按「客户端为契约真源」统一为 `items`（代码 + `tools/gen-backend-models.py` 的 `common/page` + 3 处旧测试断言），
     记偏差 **D-API-01**。教训：**分页这类跨页面通用字段，必须回到客户端适配层逐个核对，不能照抄文档**。
  2. **R-26 措辞红线**：我第一版免责声明写了「请勿理解为『已验证该模型为正品』」——否定句里也带了被禁字样，
     AC-18 的「正文无『正品』」是**字符串级**判定，会直接判失败。改为完全不含该字样的等义表述，
     并把 `forbiddenPhrases()` 收敛为「保证性断言」清单（`保证为真/保证正品/官方正版/100% 真实/绝对真实/已验证该模型为正品`）。
  3. **客户端兜底文案与 R-26 冲突**（发现 **O-01**）：`aap-client/src/utils/report-model.ts:51` 的兜底免责声明
     含「请勿理解为『已验证该模型为正品』」，客户端自身违反 R-26 的字符串级判定 → 属前端待办，后端不跟。
  4. JSON Schema 不给 `$id`：给了 https 绝对 URI 后，模型间相对 `$ref` 会被当成绝对地址去联网拉取而报
     `Failed to load json schema`；`SchemaAssert` 改为按**文件 URI** 装载，相对引用才能落在本地文件上。
  5. **验证脚本必须复核算术**：D7 五项加权与总分我手算错了两次（78.5→78.0、70.53→72.00）；
     实现是对的，被改的是**测试期望值**（用计算器复核后）。绝不能为了「让测试过」去改实现。
  6. `application.yml` 出现重复 `app.detection` 键 → Boot 4 的 YAML 解析直接启动失败（`found duplicate key`）；
     测试全量 66 例报错、报错点在「构造 mapping」。**合并键时先 grep 段落是否已存在**。
- 交付：`ReportService/ReportController/ReportViews/ReportEntity/ReportSectionEntity`（四段式解释 + 章节 A–F +
  维度对照 + 免责声明 + 权重说明 + 一票否决说明）、`NotificationService/NotificationEntity`（AC-21）、
  `RecheckService/RecheckScheduler`（AC-49，报告 30 天到期自动复测，`RECHECK` 不占日配额）、
  引擎回写闭环内嵌报告 1:1 生成（同事务，宁可整体回滚也不留「有任务无报告」）。

---

## 跨轮结论（R08 复核）

### C-01 · 禁止并发跑同一套测试库
**现象**：`proc_bad3cc109181`/`proc_2b9757f0ff91`/`proc_9bcbfe3fd21d` 等后台任务同时执行 `mvn test`，
其中一个还先做了 `drop schema public cascade`；结果出现「同一提交的用例本轮绿、下轮红」的随机失败
（`ApiContractTest` 8 例报错、`ProviderContractTest` 8 例失败、`AuthContractTest` 验证码锁定失败）。
**根因**：测试基座每例前 `TestDb.truncateAll()` + 集成测试打真实 HTTP，多个 JVM 共享 `aap_server_test` 库时
互相清表/互删字典数据，失败与被测代码无关。
**规则**：同一时刻**只允许一个** `mvn test` 进程；确需并行，必须各自独立的库（`aap_server_test_<n>`）
或给库级锁。历史上的「绿→红」波动一律先怀疑并发，再怀疑代码。
**证据**：`.agents/state/evidence/T01-run2-concurrent-dirty.txt`、`T03-run2-concurrent-dirty.txt`
（保留原始内容不改，只改文件名，避免抹掉失败记录）。

### R08 · T08 报价（QT-01…11 / AC-22…27、AC-50）—— ✅ 完成

- 红：`evidence/red-T08.txt`（HTTP 契约 7 例全红：接口不存在 → 404/E-2001）→ 3 轮修正
  → 绿：`evidence/green-T08.txt`（15 例）与全量 `evidence/green-T08-full.txt`（`Tests run: 105, Failures: 0`）
- **如实记录**：V 规则纯函数 `QuoteValidation`（V1–V17）是先写实现、后补 `QuoteValidationTest`（8 例，一次通过）。
  本轮的红线纪律落在**HTTP 契约层**（先红后绿）；纯函数层属回归护栏补齐，不做粉饰。
- 本轮踩坑（都是会带到后续任务的坑）
  1. **MyBatis-Flex 驼峰转换在「字母+数字结尾」字段上出错**：`cacheWrite1hPrice` 被转成 `cache_write1h_price`，
     实际列名是 `cache_write_1h_price` → 运行期 `PSQLException: column ... does not exist`（表现为 500 E-2001）。
     修法：显式 `@Column("cache_write_1h_price")`。**规则：列名含数字/缩写混排的一律显式标注列名，不靠约定转换。**
  2. 测试自身会触发业务规则：同一供应商下 api_key 指纹唯一（R-03），同一用例里建两个凭证若用同一个假 key →
     直接 409 E-1104。改为按序生成 key（`sk-quote-test-%08d`）。**测试夹具也要遵守业务不变量。**
  3. **错误码优先级必须显式定义**：规则族（E-1401 时段 / E-1402 阶梯 / E-1403 倍率 / E-1404 收口）与前置条件
     （E-1602 V17）必须**先于**通用 E-1001 判定；否则前端拿到 E-1001 无法定位到「哪条规则、哪个字段」。
     优先级已固化：`V17 → E-1602` > `规则族 → E-1401/1402/1403/1404` > `其余 → E-1001`。
  4. **一个错误码不能承载两种 HTTP 语义**：`E-1401` 原本既表示「时段重叠(400)」又表示「资源不存在」，
     导致 404 场景返回 400。改「资源不存在 → E-1406(404)」，记偏差 **D-API-02**，并回写清单 §2.2。
  5. **作废 ≠ 软删除**：`VOID` 保留记录（可按 `status=VOID` 审计查询，不复用 `deleted` 位），
     `deleted=true` 会让「作废后仍可追溯」失效；取舍记 **D-QUOTE-01**。
  6. **审计动作枚举扩展要先改生成器**：`AuditAction` 12→17（新增 5 个报价动作，10-PRD §7 埋点），
     改 `tools/gen-backend-models.py` 的 `ENUMS["AuditAction"]` → 重新生成 schema → 再改 Java 枚举，
     否则 schema enum 与代码枚举漂移（`AppEnvelopeTest` 那类守护断言会挂）。
  7. V15 的边界：**只有 `request_rules` 是管理端专属**，阶梯规则（`price_tier_rule`）属于报价定价本身，
     供应商可写 —— 一刀切限制会把「模型定价」页的正常保存挡掉。
- 交付：`QuoteValidation`（V1–V17 纯函数，一次收集全部错误 + 告警分档）、
  `QuoteService`（状态机 DRAFT/SUBMITTED/VOID + 前置校验 + 版本快照 + 审计 + 乐观锁）、
  `QuoteController`（QT-01…11）、8 张表实体与 Mapper、`QuoteViews`（quote-row/detail/item/version、
  price-time-rule/price-tier-rule/request-rule 契约对齐）

### R09 · T09 计费编译（QT-12、ADM-Q01、ADM-CP01…04 / 三道闸门 R-33、幂等 R-34）—— ✅ 完成

- 红→绿（纯函数层）：`evidence/T09-run1.txt`（8 例中 3 红：NPE + 档位命名 + 档位缓存价）
  → `T09-run2.txt`（1 红：缓存价口径）→ `evidence/green-T09-unit.txt`（8/8）
- 绿：`evidence/T09-run3.txt`（HTTP 7/7）、`evidence/green-T09-full.txt`（**120/120**）
- ⚠️ **如实记录（第二次出现，必须纠正）**：T09 的 HTTP 契约测试是**实现先行**写的，一次通过、没有红基线。
  红线纪律只在纯函数层成立。**从 T10 起强制「先写测试并落盘红基线，再写实现」**，包括 controller 层。
- 本轮最有价值的一次失败：**档位缓存价口径**
  - 现象：同一份报价，`BillingExpr` 求值 15250、独立期望计算 15487.5，模拟验证用例 V3b 红。
  - 根因：阶梯档位若没给 `cache_read_price`，编译器把 `cr` 项整个丢掉 → 缓存命中 token **一分钱不计**（上游白送）；
    PRD 06 §3 R2 的示例文本恰好也省了 cr 项，照字面实现就会踩进去。
  - 处置：**改实现**（档内缺价则回落明细行缓存价，记偏差 **D-COMPILE-01**），没有去改测试期望。
  - 这正是「编译器 AST 求值 vs 独立朴素计算」双路比对的价值：如果两边共用一段代码，这个洞会一直藏到对账日。
- 其它结论
  1. **档位命名是契约的一部分**：`compact()` 最初把 1024000 渲染成 `1024K`，PRD 示例是 `1M`（`t1_512K_1M`）。
     档位名会进对账账单，命名漂移等于对账口径漂移 → 已按 PRD 对齐，并用单测钉死三种形态。
  2. **期望值入口必须 null 安全**：无时段规则时 `timeMultiplier(null, …)` 直接 NPE（单测抓到）。
  3. **编译前边界检测复用 `QuoteValidation`**：提交校验与编译校验共用一套 V 规则，避免「前端能提交、后端不编译」的口径分叉。
  4. **幂等要可断言**：`source_hash` 未变 → 复用同一 `compilation_id`；内容变更 → 新产物 + `previous_expr` 旧快照。
     两条都在集成测试里直接断言（只写日志不算验证）。
  5. **管理端 token 必须在 `aap_auth_token` 落 jti**（沿用 T06 的 techOps 夹具），否则 JWT 校验直接 401。
- 交付：`BillingExpr`（AST 同时负责 render + eval）、`BillingCompiler`（R1–R6 + source_hash + 档位命名）、
  `BillingVerifier`（V1–V7 用例 + **独立期望计算** + 容差比较）、`CompileInputLoader`、
  `CompilationService`（三道闸门/幂等/旧快照/审计/边界检测）、`CompilationController` + `QT-12` 预览、
  4 张表实体与 Mapper

---

### R10 · T12 用量聚合与对账（USE-01/02、ADM-U01/02 / AC-43…46）—— ✅ 完成（4/4 端点注册）

- 说明：f3e42d6 的覆盖门禁提交后，轮次状态未续写；**R10 = T12 用量**（首轮由定时任务驱动，见开头 Run Context）。
- 红基线：`evidence/red-T12.txt`（18 例全部编译失败：`UsageMetrics` 尚不存在 —— 先写测试确实把接口设计逼出来了）
- 绿：`evidence/green-T12.txt`（**T12 全族 18/18**：契约 11 + 纯函数 6 + 降级 1）
- 全量两轮（防 flaky，串行）：`evidence/green-T12-full-run1.txt`、`green-T12-full-run2.txt`
  - **139 例 / 1 红**，两轮完全一致：唯一红是 `EndpointCoverageTest`（覆盖门禁，未注册 **45 → 41**）
  - ⚠️ 覆盖门禁存在期间**全量不可能全绿**（门禁要求 90/90）：证据文件不写「全量绿」，
    只写「除门禁外全绿 + missing 下降」，避免文件名骗人（SOP 踩坑 12）。
- 覆盖进度：`90 / 49 已注册 / 41 未注册`，T03–T09、**T12 = 4/4**；余 T10(5)、T11(11)、T13(3)、T14(22)
- **工作台 404 已解除**：`GET /api/v1/usage/summary` 上线（序号 2 工作台与序号 22 用量页共用超集响应）

- 本轮踩坑（都是会带到后续任务的坑）
  1. **PostgreSQL `sum(bigint)` 返回 `numeric`，不是 `bigint`**：`rs.getObject(..., Long.class)` 直接抛
     `conversion to class java.lang.Long from numeric not supported` —— 在 HTTP 层表现为 **500 E-2001**，
     真正根因只在服务端日志里（`GlobalExceptionHandler` 的「未捕获异常」那一行）。
     **规则：聚合查询里所有 `sum()` 一律显式 `::bigint`（金额 `sum()` 保持 numeric）。**
  2. 无数据 ≠ 0：空窗口的所有指标返回 **null**（不是 0），`provider_id`/`stat_from`/`stat_to` 仍必备；
     用例直接对 null 与空数组断言，防止以后有人「顺手兜底成 0」把「源故障」显示成「零用量」。
  3. **降级用例必须单独成类**：`@TestPropertySource` 覆盖 `app.usage.log-file` 会新建 Spring 上下文；
     混在同一类里会让整类的日志源都变成未配置（把绿色用例一起带红）。
  4. **mock 适配器也要有失败路径**：日志源未配置/不可读/格式非法 → `E-1801` + 503 +「未配置」字样，
     且**不写任何用量行**（降级不污染数据）。这条比「happy path」更能防回归。
  5. 契约字段名仍要回客户端核对（延续 D-API-01）：`/usage/share` 允许小数或百分数两种形态，
     所以 `share` 发 0–1 小数、`percent` 发 0–100，客户端 `sharePercent()` 归一都能吃下。
  6. 序列化：`sum()`/`coalesce()` 的 `jsonb_each_text` 展开要 `cross join lateral`，
     并对 `tier_distribution is null` 容忍（返回空 map，不回 0）。

- 本轮偏差（**待拍板项已标注**）
  - **D-API-03**：`docs/api/接口字段级schema.md` §2 写 `/usage/hourly` 的 data 是 `{list:[…]}`，
    但冻结清单 §1.8 与生成器 `common/page.schema.json` 都是 `{items,page,pageSize,total}`（客户端读 `items`）
    → **按清单 + 客户端真源实现 `items`**；field-level 文档那句需要同步修正（T15 文档收口）。
  - **D-API-04（待拍板）**：成本构成 `cost.input`/`cost.output` 恒为 **null** —— 小时表只有**总**折算金额，
    按 token 类型拆实际成本在 PRD/清单里**无口径**，不臆造；`cost.total` = Σ`cost_usd`（账单口径），
    `platform_fee_rate` 取「已签署合同 `aap_contract.platform_fee_rate`」（无合同 → null，客户端回退设计常量 8%），
    `platform_fee` = 费率 × 合计。
  - **D-API-05（待拍板）**：AC-45 文案写「缓存缺失标 `PARTIAL_CACHE`」，但冻结生成器
    `ENUMS["CacheParseStatus"]` 只有 `OK` / `NO_CACHE_FIELD`（PRD 11 §4/U2 同名）→ **按 schema 实现**。
    若要引入 `PARTIAL_CACHE`，必须先改生成器 + 重新生成 schema，再改代码（硬约束 1）。
  - **D-API-06**：对账 `deviation_rate` 基准 = 该供应商**最近一条 APPROVED 报价单**里各模型的
    input/output/cache_read 单价，按窗口内模型词元结构加权；**无已审报价 → null**（不臆造基准）。
    ±5% 告警阈值实现为纯函数 `UsageMetrics.deviationAlert`（单测钉死 0.05 边界不告警），
    告警通道（日志/指标）在 T15 收口。
  - **D-USAGE-01（待拍板）**：**真实 new-api Log 表拉取未接入**（无冻结契约，PRD 11 §3/§4 只说「按小时拉日志解析」）
    → 本轮聚合源为**项目内 mock 适配器** `app.usage.log-file`（JSON：`{"buckets":[…]}`），
    未配置即 `E-1801` 降级；T14 接入真实源时只需替换 `UsageService#readLogSource` 的实现。
  - **D-USAGE-02**：`month` 缺省窗口 = **当月整月** `[月初 00:00Z, 次月 00:00Z)`；`mom_rate` 与前一等长窗口比，
    `mom_saved_amount` = 上月 − 本月（可负；PRD 只有「环比」无「节省」口径 → 推断）。
    `degraded = 缓存可解析率 < 1`（缓存字段不可解析即视为数据降级）；`updated_at` = 桶最新 `collected_at`，
    `refreshed_at` = 本次聚合时刻。
  - **已知限制（非偏差，需上游配合）**：`channel_id` 为 null 的桶在 PostgreSQL 唯一索引下**互不冲突**
    （NULL 视为彼此不同），重跑这类桶会**新增行**而不是 UPSERT —— 渠道未映射（U5）必须尽早补齐 `channel_id`，
    否则 AC-44 的幂等只对已映射渠道成立。
- 交付：`UsageMetrics`（比率/单价/环比/差异率纯函数）、`UsageService`（SUMMARY 超集聚合、jsonb 档位展开、
  分页下钻、日志源 UPSERT + 游标 + 审计）、`UsageViews`（usage-summary/hourly-bucket/refresh-result 契约对齐）、
  `UsageController`（USE-01/02）、`AdminUsageController`（ADM-U01/02）、`V4__usage_sequences.sql`、
  用例 18 例（`UsageContractTest` 11 / `UsageMetricsTest` 6 / `UsageRefreshDegradedTest` 1）

## R12 · T10 审核（ADM-R01…R05，5/5 已注册）

- 红基线：`.agents/state/evidence/red-T10.txt` —— 12 例 **运行时红（断言级，不是编译红）**：用例只引用
  既有类（T03 管理端 JWT、T06 检测服务、T08 报价），全部真跑，失败一律 `404 E-1406 接口或资源不存在`
  （`/admin/reviews*` 尚未注册）。比 T12 的「编译红」更有牙齿。
- 绿：`.agents/state/evidence/green-T10.txt`（**12/12，BUILD SUCCESS**）；全量两轮
  `green-T10-full-151tests-1expected-coverage-red-run{1,2}.txt`（151 例，唯一红项仍是覆盖门禁）。
- 覆盖：`total=90 / implemented=54 / missing=36`（T10 5/5 ✅，missing 41 → 36）。
- 交付：`com.hioas.aap.review`（`ReviewTaskEntity`/`ReviewRecordEntity` + Mapper、`ReviewViews`、
  `ReviewService`、`AdminReviewController`）、`com.hioas.aap.contract`（`ContractEntity`/`ContractMapper`）、
  `QuoteService#submit` 挂「提交即入池」钩子、用例 12 例（`ReviewContractTest`）。

### 本轮踩坑（三条都是真返工，已修）

1. **同一请求内「Mapper 写 + JdbcTemplate 读」会读到写之前的状态**（最大一坑，白扔两轮）：
   领取接口库里明明已成 CLAIMED（后续请求的 Mapper 读得到），但**同一次响应里**用 JdbcTemplate 查出来的
   还是 PENDING；通过/驳回同样「少一刀」。根因是两套客户端各拿各的连接，未提交的写对另一个连接不可见
   （PG READ COMMITTED）。**规则：同一请求内的写与随后要读回的状态必须同源**——本模块因此把四条状态流转
   SQL（claim/approve/reject/reset）改到 `JdbcTemplate`，顺带拿到**真实影响行数**，乐观锁判定才成立。
   附带教训：只断言「HTTP 200 + 库里对」会漏掉「响应对不对」；本轮给状态断言加 `.as(body)`，
   响应体一进失败信息，根因立刻现形。
2. **同一实体连续两次 `update()` 会被乐观锁挡下（第二次影响 0 行且不报错）**：`QuoteService#submit`
   先更新提交态、再用同一实体把 `current_version` +1，第二次 update 的 `where version=?` 已过期 →
   库里版本原地不动，响应里的 `current_version=2` 只是**内存值**（T08 断言只看响应，因此一直没被发现）。
   后果：驳回后重提插入相同 `version_no` → 撞 `uq_quote_version` → **500 E-2001**（被本轮
   `resubmitReusesSameTask` 抓出）。修法：推进版本号前**重新读取实体**并检查影响行数为 1；
   用例补「重提后库里 `current_version=3`」断言把缺陷钉住。
3. **夹具也会写错**：技术指标快照用例只插一份 `detected_at = null` 的报告就当「最新」，而真实检测报告
   （有 `detected_at`）排序在前 → 断言红。**修夹具不改断言**：改成「1 小时前 60 分」+「1 小时后 91.5 分」
   两份，期望值仍是 91.5，顺带让「取最近一份」这条口径真正可检验。

### 本轮偏差表

| 编号 | 内容 | 理由 |
|---|---|---|
| D-STATE-02 | 通过后 `aap_quote.status = APPROVED`（非 `CONVERTED`），同事务生成 `CREATED` 合同并回写 `contract_id` | 清单 ADM-R03 只写「→ APPROVED，自动生成合同」；`CONVERTED` 语义留给 T11 签发，避免两族各自定义同一状态 |
| D-STATE-03 | `tech_reviewed_by/at` 本轮不写 | 清单内无「技术指标复核」端点（TECH_OPS 只读），不臆造写入路径 |
| D-AUDIT-01 | 领取（ASSIGN）只写 `aap_review_record`，不写 `aap_audit_log` | `AuditAction` 枚举由清单冻结且无领取值；扩枚举=改契约（硬约束 1） |
| D-AUDIT-02 | 领取使报价单进入 `REVIEWING` 的审计借用 `QUOTE_SAVE`，原因写进 summary | 同上，但「状态流转必须留痕」（A13）不能省 |
| D-API-11 | `GET /admin/reviews/records` 返回 `{items:[ReviewRecord]}`（非分页、无 page meta） | 清单该行如此定义 |

## R13 · T11 合同/打款/结算（CON-01…04、PAY-01、ADM-CT01…03、ADM-PAY01…03，11/11 已注册）

- 红基线：`.agents/state/evidence/red-T11.txt` —— 13 例 **运行时红**（用例只引用既有类，全部真跑），
  失败面是「路由未注册」（`/contracts*`、`/payments*`、`/admin/contracts*`、`/admin/payments*`、`/admin/settlements`）。
  取证方式：先写用例 → 落盘红；再把四个控制器**临时移出源码树**复跑取证（服务层留原位仍可编译），
  取完立即还原并 `ls` 核对文件回位——红基线是真实跑出来的，不是事后补的说明。
- 绿：`.agents/state/evidence/green-T11.txt`（**13/13，BUILD SUCCESS**）；全量两轮
  `green-T11-full-164tests-1expected-coverage-red-run{1,2}.txt`（164 例，唯一红项仍是覆盖门禁）。
- 覆盖：`total=90 / implemented=65 / missing=25`（T11 11/11 ✅，missing 36 → 25）。
- 交付：`com.hioas.aap.contract`（`ContractViews`、`ContractService`、`ContractSignEntity` + `Mapper`、
  `ContractController`、`AdminContractController`）、`com.hioas.aap.settlement`
  （`PaymentRecordEntity`/`SettlementStatementEntity`/`SettlementLineEntity` + Mapper、`PaymentViews`、
  `SettlementService`、`PaymentController`、`AdminPaymentController`）；用例 13 例
  （`ContractContractTest` 9 / `PaymentContractTest` 4）。
- 状态机（实现即契约）：`CREATED --ADM-CT02 issue--> PENDING_SIGN --CON-04 sign--> SUPPLIER_SIGNED
  --ADM-CT03 confirm-sign--> SIGNED`；流转一律条件 UPDATE（并发/重复操作只能一方成功 → 409 E-1601/E-1701）。
  AC-40「未签署禁打款」落在 ADM-PAY02：合同非 `SIGNED` → 409 E-1701 且打款状态/确认人不变。

### 本轮踩坑（三条，均为真返工）

1. **「可选字段」写库不能直接 `set col = ?`**：ADM-CT02 用 `currency = ?`，请求省略 `currency` 时传 null，
   撞 `aap_contract.currency NOT NULL` → HTTP 只见 **500 E-2001**（根因只在服务端日志的
   `null value in column "currency" ... violates not-null constraint` 那一行）。规则：**签发/补全是 coalesce 语义**
   —— 未提供的字段一律 `coalesce(?, 原列)` 保持原值，不做静默清空；用例补「省略 currency 后仍为 USD」钉住该缺陷。
2. **同一手机号在同一用例内二次 `POST /auth/sms/send` 会被 60 秒重发间隔挡下（E-1903）**：6 个用例在权限断言里
   又调了一次 `token(PHONE)` → 直接红。规则：**一个用例内认证令牌只取一次**并复用
   （测试库每例 `truncateAll()` 会清掉 `aap_auth_token`，令牌不能跨用例缓存）。
3. **幂等重放的响应体不能逐字比较**：`aap_idempotency_record.response_body` 是 **jsonb**，PostgreSQL 会重排键序
   并加空白 → 逐字比较必红。规则：幂等断言按 **JSON 树**比较（`JsonNode` 相等），语义不变、形状更稳；
   「同键只落一条签署记录」的断言保留。
   另有一处**测试期望写错**：`total=2, pageSize=1, page=2` 应回 1 条而不是 0 条（改的是测试期望，不是实现），
   并在越界页 `page=3` 上补空集断言。

### 本轮偏差表

| 编号 | 内容 | 理由 |
|---|---|---|
| D-API-12 | CON-03 `url` 回文件资产的 `file_key`（存储键），非限时签名 URL | 对象存储签名未接线（同 RPT-04 PDF 未接线口径）；接线后替换 |
| D-API-13 | 签发（issue）的审计动作复用 `CONTRACT_SIGN` + summary 写明「签发」 | `AuditAction` 枚举由冻结清单生成、无 `CONTRACT_ISSUE`；扩枚举=改契约（硬约束 1） |
| D-API-14 | CON-04 的 `smsCode` 只校验 6 位数字格式，不做真实短信核验 | 合同签署短信通道未接线，清单亦无发送端点；不臆造核验路径（待拍板） |
| D-API-15 | 越权/不存在统一 404 `E-1406`；`E-1701` 只用于「合同状态非法」（未签发/未签署禁打款） | 清单把 `E-1701` 挂在 CON-02/03/04 上，但错误码语义是状态类；资源不存在用 404 更不易泄露存在性 |
| D-PAY-01 | 钱包三项 = 互斥三态：`pending_settlement`=UNSETTLED、`available_balance`=PAYMENT_RECORDED、`total_settled`=CONFIRMED（VOID 不计） | 清单标注「约定，无 PRD 依据」；三态互斥避免重复计数，合计=全部有效打款金额 |
| D-STATE-04 | 签署完成后不推进 `aap_quote.status`（停留 APPROVED） | T11 范围提到「上架 PUBLISHED」，但冻结清单内无对应端点、枚举里也无 `PUBLISHED` → 不臆造（待拍板） |

## R14 · T13 站内信与审计查询（NTF-01/02、ADM-A01，3/3 已注册）—— ✅ 完成

- 红：`.agents/state/evidence/red-T13.txt`（8 例全红——三条路由未注册，真实 HTTP 全回 404 `E-1406`；
  走真实 HTTP 而不是路由探测，未注册只能是 404，不存在假红）。
- 绿：`.agents/state/evidence/green-T13.txt`（**8/8 BUILD SUCCESS**）；全量两轮
  `green-T13-full-172tests-1expected-coverage-red-run{1,2}.txt`（172 例，唯一红项仍是覆盖门禁）。
- 覆盖：`total=90 / implemented=68 / missing=22`（T13 3/3 ✅，missing 25 → 22；`registered_routes=74`）。
- 交付：`com.hioas.aap.support`（`NotificationViews`/`NotificationController`；`AuditLogViews`/
  `AuditLogController`/`AuditLogQueryService`；`NotificationService` 的读路径从 ORM 重写为 `JdbcTemplate`）；
  用例 8 例（`NotificationContractTest`）。
- 契约口径（实现即契约）：
  - **NTF-01** 响应 `{items,page,pageSize,total,unread_count}`；单条字段对齐客户端
    `aap-client/src/utils/messages-model.ts`：`id/title/content/created_at/read_at/read/is_read/event_code/biz_type/biz_id/channel/category/kind/status`；
    `kind`（detect/quote/contract/bill/system）由服务端派生（与客户端 `resolveMessageKind` 同规则），
    `read` 与 `is_read` 同值，真源是 `read_at` 空即未读。
  - **作用域**：供应商 = `recipient_type=PROVIDER` + 本人 provider；管理端 = `ADMIN` + 本人账号
    → 同一端点两端复用（清单标 `authenticated`，非仅供应商）。未认证一律 401。
  - **NTF-02 幂等**：条件 UPDATE（`... and read_at is null`）+ **读回库值** → 响应里的 `read_at`
    就是落库值本身；重复调用影响 0 行，不刷新首次已读时间（断言同时钉响应与库值，并钉 `version` 停在 1）。
  - **ADM-A01**：`TECH_OPS/SUPER_ADMIN` 可读，`BIZ_OPERATOR`/供应商 403 `E-1901`；`action` 必须命中审计字典
    （否则 `E-1001`）；时间窗半开 `[from,to)`；**真实登录链路产生的 `AUTH_LOGIN` 审计行可按 traceId 检索到**，
    且 trace_id 与该次登录响应头 `X-Trace-Id` 一致（审计不是摆设）。
- 测试期望修正（2 处，均为**断言写错**，未迁就实现）：
  1. `category=ORDER&unread=true` 的期望应为 1（夹具 800013 是 ORDER 且未读），初版误写 0；
  2. `assertThat(bad.data()).isNull()` 恒失败 —— `JsonNode#path("data")` 对 `"data":null` 返回
     **NullNode** 而不是 Java null，改用项目既有的 `isNullish(...)` 断言。

### 本轮偏差表

| 编号 | 内容 | 理由 |
|---|---|---|
| D-API-16 | ADM-A01 的 `action`/`from`/`to` 非法值回 400 `E-1001`（清单错误码列只列 `E-1901`） | 参数校验用全项目统一错误码；拼错的动作名静默回空集会让技术运营误判「没有该操作」 |
| D-API-17 | `unread_count` 口径 = 本人未读总数（与 `unread`/`category` 过滤无关） | 清单只给字段名未给口径；徽标「N 条未读」不应随列表筛选跳动（客户端注释亦按此理解） |
| D-API-18 | NTF-01/NTF-02 对管理端主体开放（管理端收件箱 `recipient_type=ADMIN`） | 清单标 `authenticated`；隔离由 recipient 维度保证，不靠 403 |
| D-API-19 | `kind`/`read`/`is_read` 为服务端派生字段（schema 中可空非必填） | 客户端 `messages-model.ts` 明确「服务端给 kind 时优先」；冗余命名是为兼容客户端容错读取 |

## R15 · T14 批次一：报告模板配置（ADM-CFG06…10，5/22 已注册）—— ✅ 完成

- 红：`.agents/state/evidence/red-T14-CFG06-10.txt`（6 例全红：三条路由未注册 → 真实 HTTP 404 `E-1406`）。
- 绿：`.agents/state/evidence/green-T14-CFG06-10.txt`（**9/9 BUILD SUCCESS**：契约 6 + 措辞单元 3）；
  全量两轮 `green-T14-CFG06-10-full-181tests-1expected-coverage-red-run{1,2}.txt`
  （181 例，唯一红项仍是覆盖门禁）。
- 覆盖：`total=90 / implemented=73 / missing=17`（T13 3 条 + T14 本批 5 条；missing 25 → 17）。
- 交付：`com.hioas.aap.adminconfig`（`ReportTemplateViews`/`ReportTemplateService`/
  `AdminReportTemplateController`/`ReportTemplateWording`）+ 迁移 `V5__report_template_sequences.sql`
  + `DocNoGenerator#reportTemplateNo()` + `ReportService#sectionCodes()`（章节枚举单一真源）；
  用例 9 例（`ReportTemplateContractTest` 6 + `ReportTemplateWordingTest` 3）。
- 口径（实现即契约）：
  - 状态机 `DRAFT --publish--> PUBLISHED`，被替代的活版 → `SUPERSEDED`：改/发布一律**条件 UPDATE**
    （`and status='DRAFT'` + 影响行数=1），重复改/重复发布 → 409 `E-1601`；发布写
    `published_at/published_by` 并落 `CONFIG_PUBLISH` 审计（可用 ADM-A01 检索到 target=report_template）。
  - **活版唯一**：任一时刻全表只有一份 `PUBLISHED`（报告生成取该份，否则「用哪一份」不确定）。
  - **R-26 措辞红线**在服务层统一校验（创建/修改同一道闸）：免责声明含「保证为真/保证正品/官方正版/
    绝对真实/已验证该模型为正品」→ 400 `E-1001`；判定是**字符串级**（否定句里出现同样失败），
    词表复用 `ReportController.forbiddenPhrases()`（不另建第二份词表）。
  - 章节 `section_order` 只能取 A–F（复用 `ReportService.SECTION_NAMES`），非空、不得重复。

### 本轮偏差表（T14 批次一）

| 编号 | 内容 | 理由 |
|---|---|---|
| D-API-20 | 报告模板「活版唯一」：发布新模板时把**其它** `PUBLISHED` 行置 `SUPERSEDED` | 清单对 ADM-CFG05（检测配置）写明「旧版置 SUPERSEDED」，模板域表结构无「族」列，按同一精神实现为全表活版唯一 |
| D-API-21 | `aap_report_template` 无「模板族」列 → 新建即新 `template_no`（`version_no` 固定 `V1`）；「同族多版本」需新端点/新列（**待拍板**） | ER 文档写明 `template_no UQ`，表结构无法表达一族多版本；不臆造端点 |
| D-API-22 | ADM-CFG06…10 放行 `TECH_OPS` + `SUPER_ADMIN`（清单只列 TECH_OPS） | `13-管理端PRD` 能力矩阵中超管为全量权限；与既有权（ADM-U01 等）同一口径 |
| D-API-23 | 修改接口未提供的字段按 coalesce 语义**保持原值**（含空白 `title` 视同省略） | 与合同签发（ADM-CT02）同一取舍：省略=保持，不是清空（R14 踩坑 1） |

## R16 · T14 批次二：检测配置版本（ADM-CFG01…05，78/90 已注册）—— ✅ 完成

- 红基线：`evidence/red-T14-CFG01-05.txt` —— 7 例全红，HTTP **404 `E-1406`「接口或资源不存在」**（= 端点未注册，不是实现 bug）。
- 绿证据：`evidence/green-T14-CFG01-05.txt`（本类 **7/7 真绿**）；
  全量两轮 `evidence/green-T14-CFG01-05-full-188tests-1expected-coverage-red-run{1,2}.txt`
  （**188 例，唯一红项仍是覆盖门禁**，run1/run2 结果一致）。
- 覆盖：`total=90 / implemented=78 / missing=12`（missing **17 → 12**）。
- 交付：`com.hioas.aap.adminconfig`（`DetectionConfigViews` / `DetectionConfigService` /
  `AdminDetectionConfigController`）+ 迁移 `V6__detection_config_sequences.sql`
  （`seq_detection_config` / `seq_detection_config_probe` / `seq_detection_config_version`）。
- 口径（实现即契约）：
  - 状态机 `DRAFT --publish--> PUBLISHED`，被替代的活版 → `SUPERSEDED`：改/发布一律**条件 UPDATE**
    （`and status='DRAFT'` + 影响行数=1），重复改/重复发布 → 409 `E-1601`；发布写 `published_at/published_by`
    并落 `CONFIG_PUBLISH` 审计（ADM-A01 可按 action 检索到 `target_type=detection_config`）。
  - **`status` 白名单**：ADM-CFG02/04 收到非 `DRAFT` 的 `status` 一律 400 `E-1001` —— 否则客户端可绕过
    发布接口造出「无 `published_at/by`、无审计」的生效配置。
  - 检测项只取 **D1–D8**（允许集合与默认名取 `ProbeScoring.PROBE_NAMES`，不另建第二份词典）；
    `weight` 存**归一化前**原始权重（归一化发生在任务打分、只对计分项）；缺省超时按 ER：
    D1–D3/D6–D8 = 180s、D4/D5 = 600s；`params` 原样存 jsonb。
  - 修改是 **coalesce 语义**（省略=保持）；`probes` 一旦提供即**整体替换**（旧项软删 + 新项插入），
    避免「部分更新后权重集合不自洽」。
  - 列表接口**逐份带检测项明细**（管理端列表页要展示启停/权重，只回壳等于列表页不可用）。

### 本轮踩坑（第 1 条会伪装成“实现已好”）

1. **`map()` 里 `probes` 传了 `false` 却忘了在 `detail()` 里补**：`create` 返回的是 `detail(id)`，
   若 `detail()` 不补检测项，响应就是「id 有、`probes: []`」—— 只看 HTTP 200 + 库里有 3 行会**误判为绿**，
   只有 `assertThat(data.path("probes").size()).isEqualTo(3)` 这种响应体断言才抓得到。规则：写+读回响应的
   视图必须在同一处补齐全部子集合（与踩坑 17 同源：状态/明细断言都钉响应体）。
2. **`weight` 列是 `numeric(6,4)`**：负权重/超大权重不在入口拦，入库会炸成 **500 `E-2001`**
   （与踩坑 13 同族，根因只在服务端日志）。规则：列宽约束在服务层做前置校验（`0 ~ 99.9999`），
   400 里带字段名 `probes.weight`。
3. **红基线的错误码要读懂再动手**：本轮红是 404 `E-1406`（路由缺失），不是 400/500 ——
   若把红基线当实现 bug 去改实现，方向就错了。先看状态码判断「缺路由 / 缺校验 / 缺数据」。

### 本轮偏差表（T14 批次二）

| 编号 | 内容 | 理由 |
|---|---|---|
| D-API-24 | `version_no` 由序列生成、**全表唯一** → 每次新建即新版本（`V1`、`V2`…）；「同族多版本」在当前表结构下不可表达（**待拍板**） | ER 写明 `uq_detection_config_version`；用 `count(*)+1` 在并发下重号，序列并发安全、重启不跳号（与 D-API-21 同一取舍） |
| D-API-25 | 已发布配置**暂未被检测任务消费**：`DetectionService` 仍按 `ProbeScoring` 默认权重打分，`aap_detection_job.config_snapshot` 也未落配置快照 | 接入点跨任务族（T06 检测任务），需人拍板；**不静默改检测口径**（待拍板） |
| D-API-26 | ADM-CFG01…05 放行 `TECH_OPS` + `SUPER_ADMIN`（清单只列 TECH_OPS） | 沿用 D-API-22 的能力矩阵口径（超管全量权限） |
| D-API-27 | ADM-CFG01 额外支持可选 `status` 过滤（清单 `query_params` 只有 `page`/`pageSize`） | 纯附加过滤参数（缺省=不过滤），与 ADM-CFG06 同一做法，不改既有语义 |

## R17 · T14 批次三：new-api 同步运维（ADM-S01…06，84/90 已注册）—— ✅ 完成

- 红基线：`evidence/red-T14-sync.txt`（原始 `evidence/red-T14-sync-raw.txt`）—— **8 例全红**，
  首个断言都是 HTTP **404 `E-1406`「接口或资源不存在」**（= 六条 `/admin/sync/**`、`/admin/channel-bindings`
  路由未注册，不是实现 bug；与踩坑 23 的状态码判读一致）。
- 绿证据：`evidence/green-T14-sync.txt`（定向 **8/8 真绿**，原始 `green-T14-sync-try3.txt`）；
  全量两轮 `evidence/green-T14-sync-full-run{1,2}.txt`（**196 例，唯一红项仍是覆盖门禁**，两轮一致）。
- 覆盖：`total=90 / implemented=84 / missing=6`（missing **12 → 6**）。
- 交付：`com.hioas.aap.sync`（`SyncViews` / `NewApiSyncClient` / `SyncAttemptRecorder` /
  `SyncAdminService` / `AdminSyncController`）+ 迁移 `V7__sync_operation_sequences.sql`（`seq_sync_operation`）。
- 口径（实现即契约）：
  - **重试退避与上限（AC-35）**：第 1 次立即 → `+30s` → `+2min` → `+8min` → `+30min`，**≤5 次**；
    第 5 次转 `MANUAL`（再重试 409 `E-1601`，且被拒的重试不推进 `attempt_count`）；
    鉴权类（上游 401/403）**不重试**直接 `MANUAL`（PRD §5 / A8）。只允许从 `FAILED`/`MANUAL` 重试。
  - **`E-1505`（403「同步接口权限不足」）= new-api 侧拒绝**：端点 `readonly=true` 时的写操作，
    或上游返回 401/403。清单只在 S03/S05/S06 列该码 —— 这三条正是会碰上游的接口，纯 DB 读的
    S01/S02/S04 不产生它（见偏差 `D-SYNC-01`，语义**待拍板**）。
  - **启停走读前写后三段式（AC-34）**：读现值 → 写 → 回读比对，成功才置态并回填
    `last_synced_at` + `last_readback_hash`；**回读不一致 → 502 `E-1501` 且库里状态保持原值**
    （只更新回读摘要，等人工介入，绝不谎报成功）。同目标状态 = **幂等**（不打上游）。
  - 渠道状态机：仅 `SYNCED`/`ENABLED`/`DISABLED` 可启停（`NOT_SYNCED` 等 → 409 `E-1601`）。
  - 任务详情/列表/重试响应**统一带 `operations`**：子集合在一处补齐（列表复用详情映射，踩坑 22）。
  - 每次重试都落一行 `aap_sync_operation`（attempt_no + result + error）与一条 `SYNC_EXECUTE` 审计；
    失败路径**先落库再抛错**（独立事务 `SyncAttemptRecorder`，踩坑 2）。

### 本轮踩坑

1. **`channel_id` 是 `bigint`，视图契约是 `integer`**：`rs.getObject("channel_id", Integer.class)` 抛
   `conversion to class java.lang.Integer from int8 not supported`，HTTP 层只看到 **500 `E-2001`**，
   根因只在服务端日志（与踩坑 13 的聚合 `numeric` 同族）。规则：**先按 `Long` 读、再显式收窄**，
   别让列的物理类型去猜视图契约类型。
2. **契约里的 ID 是 string，服务层要 Long**：视图字段（`binding_id`/`endpoint_id`）对外是 string，
   直接回传内部方法会编译不过；统一加 `toId()`，非法值 → 400 `E-1001`（不静默当 null）。
3. **夹具的时间参数要带 `::timestamptz`**：`insert ... values (?, ...)` 里 String 参数直落 timestamptz 列会报
   「column is of type timestamp with time zone but expression is of type character varying」；
   首轮红基线里混进 4 个这类夹具错误 —— 按纪律**修夹具不改期望值**，重跑得到纯净红基线。
4. **期望值先算再写**：`taskCount()` 断言写了 4 而夹具只有 3 条（踩坑 6/19 的重演）—— 改期望值。
5. **重试类失败用例必须在同一请求里落库**：调用方抛 `E-1501` 时若无独立事务，任务状态与操作明细会一起回滚，
   「502 之后任务仍是原状态」看起来像实现没生效（踩坑 2）。

### 本轮偏差表（T14 批次三）

| 编号 | 内容 | 理由 |
|---|---|---|
| D-SYNC-01 | `E-1505` 解释为**上游/new-api 侧拒绝**（端点只读、上游 401/403），角色不足仍是全局 `E-1901`（**待拍板**：若产品意图是「非 TECH_OPS 访问同步接口也回 E-1505」，需改安全层错误码，影响面在 §4 错误码表） | 清单只在 S03/S05/S06 列 E-1505，而这三条正是会碰上游的接口；纯 DB 读的 S01/S02/S04 未列 |
| D-SYNC-02 | `NewApiSyncClient` 的**写侧路径为 mock 口径**：`GET {base}/models`、`PUT {base}/api/channel/`、`GET {base}/api/channel/{id}`（**待拍板**） | PRD §3 只冻结字段映射与幂等键，未冻结 new-api HTTP 契约（new-api 侧需源码改造）；接入真实实现只替换本类路径 |
| D-SYNC-03 | 本批次只做**运维接口**（查/重试/启停/读上游），不含同步任务执行器与调度（谁消费 `PENDING`、写价如何落编译产物） | 执行器跨 T09/T15（`SYNC_WRITE_PRICE` 与编译器接线），需人拍板后再动 |
| D-SYNC-04 | ADM-S01…06 放行 `TECH_OPS` + `SUPER_ADMIN`（清单只列 TECH_OPS） | 沿用 D-API-22/26 的能力矩阵口径（超管全量权限） |
| D-SYNC-05 | 端点解析失败（`binding.endpoint_id` 指向不存在/非 ACTIVE 的端点）时按「未接 new-api」处理：重试直接入队、启停只改本地状态（**待拍板**：是否应报 502） | 联调期允许「本地先行」；不静默假装做过上游回读（回读摘要留空以区分） |

## R18 · T14 批次四：管理端供应商 / 凭证 / 报价对比（ADM-P01…03、ADM-C01/02、ADM-Q02，**90/90 已注册**）—— ✅ 完成

红基线：`evidence/red-T14-adm-pcq.txt`（原始 `red-T14-adm-pcq-raw.txt`）
  `mvn test -Dtest=AdminProviderContractTest,AdminCredentialContractTest,AdminQuoteCompareContractTest`
  → **Tests run: 8, Failures: 8**，8 条红全是 `404 {"code":"E-1406"}`（缺路由；踩坑 23 的判定特征），
  无夹具 SQL 错误、无编译错误 —— 一次干净红。

绿基线：`evidence/green-T14-batch4.txt`（原始 `green-T14-batch4-full-run1.txt` / `-run2.txt`）
  run1 = run2 = **Tests run: 204, Failures: 0, Errors: 0** → BUILD SUCCESS（连跑一致，无 flaky）。
  `coverage-report.json`：total 90 / implemented 90 / **missing 0** → `EndpointCoverageTest` **转绿**。
  这也是本仓库第一次**真的**能写「全量全绿」（196 → 204 例）；踩坑 14 的限定写法在本轮起不再适用。

### 本轮踩坑（两条，都是本轮实打实撞出来的）

1. **`mapper.update(entity)` 清不掉列 → 留痕清除必须 `update(entity, false)`**：
   ADM-P03 恢复要把 `status_before_suspend` / `suspended_at` 置回 NULL，但 MyBatis-Flex 的
   `update(entity)` **默认忽略 null 字段**（`update(entity, true)` 语义），结果是「响应说恢复了、
   库里留痕还在」；下次暂停还会复用旧值。改用 `update(entity, false)`（ignoreNulls=false）显式写 NULL。
   注意它同时要求**先读出完整实体再改**（否则会把没读到的列一起写成 NULL）——本实现全程
   `selectOneById` → 改字段 → `update(entity, false)` → 再 `selectOneById` 回读。
2. **写后必须重读再映射响应（踩坑 17/18 的乐观锁变体）**：`version` 列由乐观锁插件 +1，
   若响应用内存实体，`status` 对了但 `version` 是旧值（「响应说 1、库里是 2」这类自相矛盾）。
   本实现 `suspend` / `resume` 都在 `update` 之后 `requireById(...)` 重读，测试断言**同时钉**
   `响应.status/version` 与 `库里 status/suspended_at/status_before_suspend`。

### 本轮偏差表（T14 批次四）

| 编号 | 内容 | 理由 |
|---|---|---|
| D-ADM-01 | ADM-P03「恢复」回到**暂停前状态**：新增列 `aap_provider.status_before_suspend`（V8），暂停时写入、恢复时读回并清空；**遗留数据**（该列为空，如迁移前被暂停的行）回退口径 = 有 `published_at` → `PUBLISHED`，否则 → `DETECT_PASSED`（**待拍板**：若产品要求「一律回 PUBLISHED」或「必须人工指定」，替换这一段即可） | 清单/ER 只有 `suspended_at`（暂停时刻），没有暂停前**状态**；只凭 `status + suspended_at` 无法区分暂停前是 `DETECT_PASSED` 还是 `PUBLISHED`。与其猜一个固定回退值，不如显式留痕 |
| D-ADM-02 | ADM-Q02 的字段级口径：`quoteIds` 逗号分隔、**按「旧 → 新」顺序**，取**首单 vs 末单**的当前明细；`items` 按模型名升序 × 固定价字段序，只输出「至少一侧有值」的行；`change_rate` 为**百分数**（四位小数 HALF_UP），单侧缺失或旧值 0 → `null`；**不做币种换算**（两侧币种不同原样输出）；少于两个 ID → 400 `E-1001` | 清单只写「→ `{items:[QuoteCompare]}`（旧值/新值/涨跌幅 A8）」，未冻结字段级语义；PRD `13-管理端PRD.md` §5.3/§5.6 的「报价历史对比（该供应商历次报价）」指向多单对比。**待拍板**：是否需要支持「单个报价单的上一版本 vs 当前版本」对比（当前不支持，需先改清单） |
| D-ADM-03 | ADM-Q02 只放行 `BIZ_OPERATOR` + `SUPER_ADMIN`（不放技术运营） | 冻结清单 ADM-Q02 的角色列只有 `BIZ_OPERATOR,SUPER_ADMIN`；PRD §5.6 的表格把技术运营也勾了「可看」。**冲突取清单**（硬约束 1：清单为冻结真源），已在此显式记录待拍板 |
| D-ADM-04 | 生成器的 `LIST_RESPONSE_MODELS` 会把**单对象**响应（ADM-P02/P03）也包成 `data:{list:[...]}`，而 ADM-Q02（非分页 `{items:[...]}`）被包成 `data:{page,pageSize,total,list}` | 与实现不符的是**生成器的包装策略**，不是实现：清单 §2.4 明写 `{items:[QuoteCompare]}`，`PageResult` 也是 `items`（客户端真源，D-API-03 同一问题）。实现按**清单**落地（P02/P03 回单对象、Q02 回 `{items}`）；生成器待与 D-API-03 一并收口，避免只为 3 条接口手改 |
| D-ADM-05 | `PROVIDER_RESUME` 进入审计动作枚举（12→18 累计 18 个），并**先改生成器再改代码**（`tools/gen-backend-models.py` 的 `AuditAction` + 重跑生成 schema/openapi） | 恢复是独立的安全相关动作，复用 `PROVIDER_SUSPEND` 会让审计无法区分「谁暂停 / 谁恢复」；枚举属冻结产物，先改单一事实源（硬约束 1/2）。已同步 `docs/backend/02-API接口模型清单.md` §6 变更记录 |

## 未决与下一步

- 上一轮已完成：**T14 批次四 · 管理端供应商 / 凭证 / 报价对比**（R18，ADM-P01…03、ADM-C01/02、ADM-Q02，
  **90/90 已注册，missing 0，全量 204 例全绿**）。
- 下一轮：**T15 端到端验收与交付** —— 冻结清单已 100% 注册，覆盖门禁不再是红项；剩余工作转为
  端到端联调（`aap-client` 指向本服务跑页面取数）、容器化交付与 `aap-server/README.md` 运行说明。

- **待拍板（本轮新增）**
  1. **D-API-12**：对象存储签名/限时 URL 的接线方式（合同 PDF 与报告 PDF 是同一问题）。
  2. **D-API-14**：合同短信签署是否走真实短信核验（若走，需先把「合同签署验证码发送」端点写进清单再实现）。
  3. **D-STATE-04**：「上架 PUBLISHED」由哪个端点触发、`aap_quote` 何时转 `CONVERTED`（清单未定义）。
  4. **D-PAY-01**：钱包三项口径需产品确认（清单自述无 PRD 依据）。
  5. **D-API-24**（R16 新增）：检测配置「同族多版本」当前表结构不可表达（`version_no` 全表唯一 → 新建即新版本）；
     若要「同一配置的草稿/发布演进」，需要新列或新端点。
  6. **D-API-25**（R16 新增）：已发布检测配置何时被**检测任务**消费（`aap_detection_job.config_snapshot`
     的接入点跨 T06 检测任务族，本期未动检测打分口径）。
  7. **D-SYNC-01**（R17 新增）：`E-1505` 的语义归属 —— 本实现按「上游/new-api 侧拒绝」落地；
     若产品意图是「非 TECH_OPS 访问同步接口也回 E-1505」，需改安全层错误码（影响 §4 错误码表）。
  8. **D-SYNC-02**（R17 新增）：new-api 的真实 HTTP 契约（写渠道/读回读的路径与方法）需 new-api 侧提供后替换 mock 口径。
  9. **D-SYNC-03**（R17 新增）：同步任务**执行器**（谁消费 `PENDING`、`WRITE_PRICE` 如何与编译产物接线）归 T15 还是本期补齐。
  10. **D-SYNC-05**（R17 新增）：端点解析失败时「本地先行」还是直接 502。
  11. **D-ADM-01**（R18 新增）：供应商恢复的「暂停前状态缺失」回退口径（当前：有 `published_at` → `PUBLISHED`，否则 → `DETECT_PASSED`）。
  12. **D-ADM-02**（R18 新增）：报价对比是否需要「同一报价单上一版本 vs 当前版本」；`change_rate` 用百分数还是比值。
  13. **D-ADM-03**（R18 新增）：ADM-Q02 是否放行技术运营（清单不放、PRD §5.6 放，当前取清单）。
- **待拍板（沿用）**：D-API-05（`PARTIAL_CACHE` 是否入枚举）、D-USAGE-01（new-api 用量日志源契约）、
  D-API-03（`docs/api/接口字段级schema.md` §2 的 `{list}` → `{items}` 回改，含 D-ADM-04 的生成器包装策略）。
- 剩余任务：**仅 T15 端到端验收与交付**（T14 于 R18 收口；`docs/backend/03-任务与TDD计划.md` §1 为完整清单），
  以及 `aap-server/README.md` 运行说明。
- 覆盖门禁纪律（R18 起更新）：`EndpointCoverageTest` 已 **90/90 转绿**（missing 0），不再是红项；
  纪律改为「**任何端点新增/改动都必须先改 `tools/gen-backend-models.py` 的 PATHS 表 + 冻结清单，再改代码**」——
  门禁会把「代码里注册了但清单没有」与「清单有但没注册」同时暴露出来，双向都会红。
- **待前端处理（O-01）**：`aap-client/src/utils/report-model.ts:51` 兜底免责声明含 R-26 禁用字样，建议改为与
  服务端 `ReportService.DISCLAIMER` 同文案。
- 待办（跨轮）：`aap-server/README.md` 运行说明；T15 时把 `aap-client` 的 `baseUrl` 指向本服务做联调截图。

## R19（2026-09-18 11:09–11:11）· 验收巡检：90/90 全绿复验（**不改代码**）

**触发条件**：`coverage-report.json` = total 90 / implemented 90 / **missing 0**，任务规则第 4 步生效
→ 本轮**不写任何代码、不动任何断言**，只做独立复验并留证。

**复验结果（真实执行，非自述）**

| 项 | 结果 |
|---|---|
| 全量 run1（工作树现状） | `Tests run: 204, Failures: 0, Errors: 0, Skipped: 0` / `BUILD SUCCESS` |
| 全量 run2（防 flaky 第二轮） | 同上，完全一致 / `Total time: 50.812 s` |
| 覆盖门禁 | `EndpointCoverageTest` `Tests run: 1, Failures: 0` → 90/90 转绿（registered_routes=96，not_registered=[]） |
| 证据文件 | `evidence/green-verify-R19-full-204tests-run1.txt`、`green-verify-R19-full-204tests-run2.txt` |
| 台账 | `evidence/coverage-history.txt` 追加 3 行（2 行本轮 + 1 行时间戳更正） |

**本轮观察（供下一轮参考，均未改代码）**

1. **工作树里混着他方未提交的改动**（`application.yml` 把 `expose-code` 改为 `${AAP_SMS_EXPOSE_CODE:false}`、
   `application-test.yml` 把日志目录拆到 `logs/test`、`log4j2-spring.xml`、`aap-client/vite.config.ts`）。
   本轮的全量复验**就是在这些未提交改动之上**跑的，204 例仍全绿 → 说明这些改动当前不破坏测试；
   但它们**不属于本任务**，本轮一个 hunk 都没提交（只提交 `.agents/state/` 下自己的证据与台账）。
2. **覆盖门禁现在是双向的**：既查「清单有但没注册」，也查「代码注册了但清单没有」。90/90 之后
   任何端点改动都必须先改 `tools/gen-backend-models.py` 的 PATHS 表 + 冻结清单，否则门禁会红。
3. **常驻进程**：`jps` 显示 `com.hioas.aap.AapServerApplication`（PID 6220，08:03 启动）仍在跑，
   属他方联调进程，本轮只做只读观察，未 kill、未重启；测试库 `aap_server_test` 与之无冲突
   （本轮两轮连跑结果完全一致，无幽灵失败）。
4. **台账时间戳卫生**：上一轮写入的 11:05/11:08/11:18 与证据 mtime（10:54/10:55/10:58）不符，
   已在 `coverage-history.txt` 显式更正（结论不变）。教训：**台账时间戳应当场用 `date` 取**，
   不要事后凭印象补写 —— 否则「证据文件名/mtime/台账」三者的时间线会对不上，评审时无法互证。

**未决与下一步（不变）**：仅剩 T15 端到端验收与交付（`aap-server/README.md` 运行说明 +
`aap-client` 指向本服务联调截图）；`docs/backend/03-任务与TDD计划.md` §1 为完整清单。
待拍板事项见上一节（D-API-12/14、D-STATE-04、D-PAY-01、D-API-24/25、D-SYNC-01…05、D-ADM-01…03 等），
本轮无新增、无变化。
