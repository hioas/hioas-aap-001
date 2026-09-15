# 零歧义执行规格spec

# 零歧义执行规格（spec）

> 读者：AI 编码 agent。自包含，凡给出确切方法/路径/字段/公式/边界值的原样实现，不得改写/优化。禁止新增 new-api 接口调用、禁止改 new-api 源码、禁止臆造字段。

## 0. 术语表

AAP、供应商/提供方、运营方/需求方、new-api、凭证（base\_url+api\_key+model\_list）、检测任务 DetectionJob、检测项 Probe（D1–D8）、检测报告、报价单 Quote、明细行 QuoteItem、计费表达式 BillingExpr（带 v1: 前缀）、上架 Publish、用量 Usage、一票否决 Veto、source\_hash、基线库。

## 1. 目标与范围

北极星指标：供应商注册到上架中位时长 ≤3 天（系统侧 ≤2 小时）；质量指标：检测通过后 30 天内复测"疑似降级"比例 <2%。

In Scope S1–S13：注册登录、档案、凭证、检测引擎（D1–D8）、报告、通知、报价、审核、合同打款、计费编译、new-api 同步、小时用量、审计。
Out of Scope O1–O7：new-api 源码改造、资金流转、线上电子签、benchmark 排行、客户端用户体系改造、D8 计入总分、请求级加价供应商侧自助。

## 2. 技术栈与工程约束（强制）

Java 25（`<java.version>25</java.version>`）；版本治理 `import com.hioas.framework:hioas-dependencies:1.0.0-SNAPSHOT`（type=pom, scope=import）；Spring Boot 由 BOM 管理 `4.1.1`（项目 POM 不得自指定版本）；Maven 多模块 `<revision>1.0.0-SNAPSHOT</revision>`；PostgreSQL；uni-app/Taro（供应商端）+ Vue3+Element Plus+ECharts（管理端）。
POM 约束：聚合 POM parent 指向 hioas-parent；dependencyManagement 含 hioas-dependencies；除 BOM 外第三方不写 version；log4j2。

## 3. 领域模型与实体（字段级，20 个实体）

ProviderAccount（phone 密文+phone\_masked+wx\_openid+role+status）、Provider（provider\_code AAP-P-{6位}、short\_name、company\_name、uscc、contact、qualification\_files、status、recheck\_interval\_days、manual\_override、override\_reason）、Credential（base\_url、api\_key\_cipher AES-256-GCM 格式 base64(iv||ct||tag)、api\_key\_masked、key\_fingerprint SHA-256、model\_list、is\_primary、status；UNIQUE(provider\_id,key\_fingerprint)）、ProviderChallenge、DetectionConfig、DetectionJob（config\_snapshot、total\_score、result、confidence）、DetectionResult（UNIQUE(job\_id,probe\_code)）、BaselineModel、ReportTemplate、Report、Quote（quote\_no、status、source\_hash）、QuoteItem（八大单价+time\_rule+tier\_rule+request\_rules）、CompileArtifact（expr、verified、is\_active）、Contract（sign\_channel OFFLINE）、Payment、ChannelLink（channel\_name AAP-{short\_name}-{seq}、tag=provider\_code、sync\_status）、SyncTask（idempotency\_key）、UsageHourly（UNIQUE(stat\_hour,channel\_id,model\_name)）、AuditLog、Notification。

金额 numeric(18,6) 单位 \$/1M tokens 或 USD；时间 timestamptz UTC。

## 4. 状态机定义（全部枚举与合法流转）

ProviderStatus：PENDING\_CREDENTIAL/DETECTING/DETECT\_FAILED/DETECT\_PASSED/QUOTING/QUOTE\_SUBMITTED/CONTRACT\_PENDING/SIGNED/PAID/PUBLISHED/SUSPENDED/TERMINATED。任何不在合法流转表内的变更拒绝 E-1601。
DetectionJobStatus：QUEUED/RUNNING/PARTIAL\_DONE/COMPLETED/REPORT\_GENERATED/FAILED。
ProbeStatus：SUCCESS/FAILED/SKIPPED/NOT\_MEASURABLE。
CredentialStatus：PENDING\_PRECHECK/PRECHECK\_PASSED/PRECHECK\_FAILED/ACTIVE/INVALID。
QuoteStatus：DRAFT/SUBMITTED/REVIEWING/REJECTED/APPROVED/CONVERTED。
ContractStatus：DRAFT/PENDING\_SIGN/SIGNED/ARCHIVED。
PaymentStatus：UNPAID/RECORDED/CONFIRMED。
SyncStatus：PENDING/SYNCING/SYNCED/PARTIAL\_FAILED/ENABLED/DISABLED。
TriggerType：FIRST/MANUAL/SCHEDULED。Role：SUPPLIER/BIZ\_OPERATOR/TECH\_OPS/SUPER\_ADMIN。

## 5. 业务规则清单（R-xx，53 条）

关键规则：R-01 手机号 `^1[3-9]\d{9}$`；R-02 验证码 6 位 300s 60s 频控 5 次锁 15 分钟；R-03 凭证唯一 fingerprint 重复 E-1104；R-04 base\_url 规范化去尾斜杠保留 /v1；R-05 凭证脱敏 `{前4}***{后4}` 明文仅 SUPER\_ADMIN+二次验证+审计；R-06 AES-256-GCM 密钥与库分离；R-07 SSRF 出站防护 E-1201；R-08 检测互斥 E-1301；R-09 供应商日配额 5 次；R-10 探测重试 ≤2 次 401/403 不重试；R-11 单项超时 D1–D3/D6–D8 180s D4/D5 600s；R-12 压测成本保护默认 \$2/任务；R-13 RPM 硬上限 60 req/s；R-14~~R-18 D1–D6 打分公式；R-19 D7 打分加权合成；R-20 D7 一票否决 <40；R-21 D7 降级告警；R-22 D8 不计分；R-23 权重归一化 Σ=1；R-24 总分 round 2 位；R-25 通过判定四分支（否决→FAIL；≥pass\_score 含不可测→MANUAL\_REVIEW 否则 PASS；≥pass\_score−10→MANUAL\_REVIEW；否则 FAIL）；R-26 报告措辞禁"正品"；R-27~~R-32 报价校验；R-33 编译三闸门；R-34 编译幂等 source\_hash；R-35 写前对比写后回读；R-36\~R-38 渠道命名/tag/group；R-39 同步幂等；R-40 同步重试 30s/2m/10m/30m/2h ≤5 次；R-41 合同线下；R-42 打款仅记录；R-43 上架前置；R-44 启停 tag；R-45 用量聚合幂等；R-46 缓存字段解析；R-47 审计强制；R-47a 人工放行 override\_reason 必填；R-48 手机号脱敏。

## 6. 与 new-api 的集成契约（确切接口）

建渠道 `POST /api/channel/`（AdminAuth+ChannelSensitiveWrite），请求体映射 name/type/key/base\_url/models/group/model\_mapping/priority/weight/tag/status(2)/remark；改渠道 `PUT /api/channel/`（ChannelWrite，必含 id）；查询 `GET /api/channel/:id`（回读，key 脱敏）；启停 `POST /api/channel/:id/status` + `POST /api/channel/tag/enabled|disabled`；同步模型 `POST /api/models/sync_upstream`。
写价格（option 契约）：写 `billing_setting.billing_expr`（map\[模型名]表达式 JSON 字符串）+ `billing_setting.billing_mode`；适配器 BillingOptionWriter 两实现——DB（默认，直连 PG `INSERT ... ON CONFLICT(key) DO UPDATE`，仅写上述两键）/ HTTP（M1 首日实测后才启用）；写前对比+写后回读。
用量读取：直连 new-api PG 读 logs 表（只读 SELECT），不调接口。

## 7. 检测引擎 8 项算法规格（D1–D8）

D1 TTFT：stream=true 测首 chunk，samples=10 interval=1000ms，score=clamp(100\*(3000−p50)/(3000−200))，样本<3 FAILED。
D2 P50/TPS：500 token 输入 256 输出，score=clamp(100\*(tps−5)/(80−5))。
D3 一致性：temp=0 top\_p=1 n=8 并发，score=一致率\*100。
D4 RPM：阶梯 5 req/s 起每 5s +5，硬上限 60，无申报 NOT\_MEASURABLE。
D5 TPM：60s 窗口最大化 token，无申报 NOT\_MEASURABLE。
D6 缓存命中：≥2000 token 两次同 prompt，OpenAI cached\_tokens / Claude cache\_read\_input\_tokens，命中 100 未命中 0 字段缺失 NOT\_MEASURABLE。
D7 模型指纹：5 子证据线（自我认知 0.15/Tokenizer 指纹 0.25/行为题库 40 题 0.35/概率 logprobs 0.15/上下文边界 0.10），加权合成，score<40 一票否决，置信度 ≥4 高/3 中/≤2 低。
D8 真实源：6 证据线（DNS/TLS/响应头/错误格式/模型列表/时间特征），仅证据不计分。

## 8. 计费表达式编译规则（确定性算法 + C1–C10 示例）

编译算法：校验→base\_term→build\_tier\_tree（len 分档半开区间）→wrap\_time（hour/weekday）→wrap\_request（|||）→"v1: " 前缀→模拟校验→source\_hash。
价格表达式：`p * input + c * output + cr * cache_read + cc * cache_write + cc1h * cache_write_1h + img * ...`。
档位命名 `t{index}_{label}` 或 `t{index}_{label}.{peak|offpeak}`。

C1 基础 `v1: tier("base", p * 2.5 + c * 15)`；C2+缓存读 `+ cr * 0.25`；C3 Claude 系 `+ cr*0.3 + cc*3.75 + cc1h*6`；C4 阶梯 3 档；C5 阶梯 MULTIPLY；C6 峰谷 hour 条件×2；C7 跨零点 `hour>=22 || hour<6`；C8 工作日/周末 weekday；C9 阶梯×峰谷组合（外层 len 内层 hour 全量内联）；C10 请求级 `|||when(header("anthropic-beta") has "fast-mode") * 6`。

模拟校验 V1–V6（基础/缓存/阶梯边界/时段边界/组合/跨零点），失败定位字段。

## 9. 错误码表

E-1001 参数校验；E-1101~~E-1104 预检/重复；E-1201~~E-1205 SSRF；E-1301~~E-1305 检测；E-1401~~E-1407 报价/编译（E-1401 时段重叠、E-1402 阶梯空洞、E-1403 倍率非法、E-1405 模拟校验失败、E-1407 未确认写入）；E-1501\~E-1505 同步；E-1601 状态非法流转、E-1602 未通过检测报报价；E-1701 合同未签署打款；E-1801 用量聚合失败；E-1901/1902/1903 权限/认证/限流；E-2001 内部错误。统一响应 `{"code":"0|E-xxxx","message":"...","data":{}}`。

## 10. 非功能约束

安全：凭证 AES-256-GCM 密文 base64(iv||ct||tag)；脱敏 key `{前4}***{后4}` 手机号 `{前3}****{后4}`；明文仅超管二次验证+审计；SSRF 拒绝 RFC1918/RFC6598/环回/链路本地/组播/元数据地址、仅 http/https、重定向≤3、响应体≤10MiB；压测限流；审计四类操作。
性能：单次检测≤15 分钟、管理端列表 P95<500ms、供应商端首屏 P95<800ms、聚合单窗口≤60s。
可用性：同步失败不阻塞、检测故障不阻塞报价（人工放行）、用量聚合幂等、编译写 new-api 最终一致。
合规：措辞不宣称保证为真、合同主体信息完整、手机号脱敏。

## 11. 追踪矩阵

需求→规格：F1→§3.16+§7.1；F2–F4→§10+C1–C10；F5→§7.6；F6→§7.1–7.5；F7/F8→§3.18+R-45/R-46；状态机→§4+§6；指纹概率→§8.7+R-20/R-21/R-26；合同线下→§4.6+R-41；打款仅记录→§4.7+R-42；缓存方案 C→§3.18+R-46；红线→R-33+§10.6。
