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

## 未决与下一步

- 下一轮：**R10 · T10 审核**（ADM-R01…05，AC-32…35）——领取（乐观锁 E1）、通过（A9 自动生成合同）、
  驳回（必填原因码定位到 item_id/字段）、审核记录。**本轮起强制先红后绿，含 controller 层。**
- 剩余任务：T10 审核、T11 合同/打款/结算、T12 用量、T13 站内信/审计/配置、
  T14 同步与配置、T15 端到端联调与容器化交付（`docs/backend/03-任务与TDD计划.md` §1 为完整清单）。
- **待前端处理（O-01）**：`aap-client/src/utils/report-model.ts:51` 兜底免责声明含 R-26 禁用字样，建议改为与
  服务端 `ReportService.DISCLAIMER` 同文案。
- 待办（跨轮）：`aap-server/README.md` 运行说明；T15 时把 `aap-client` 的 `baseUrl` 指向本服务做联调截图。
