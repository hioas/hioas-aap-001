# 报价与合同结算PRD

# PRD — 报价与合同结算

> 对应模块 M7（报价）、M8（审核）、M9（合同与结算）。报价单是编译的唯一事实源，本册定义"怎么填、怎么审、怎么签"。

## 1. 目标与范围

把"Excel/微信谈价 → 人脑算倍率 → 手工配置"变成结构化填单 + 双通道审核 + 线下签署 + 打款留痕 + 归档闭环。

| 模块      | 本期范围                                          | 明确不做                   |
| ------- | --------------------------------------------- | ---------------------- |
| M7 报价   | 多模型明细行、暂存/提交/撤回/驳回重提、时段价、阶梯价、缓存价、请求级加价（管理端高级） | 同行竞价自动排名               |
| M8 审核   | 技术指标复核 + 价格审核、通过/驳回（必填原因）、历史对比                | 多级会签审批流                |
| M9 合同结算 | 生成/上传/签署状态机、线下留痕、打款状态与凭证、归档                   | 线上电子签（一期 OFFLINE）、资金流转 |

**红线**：报价审核通过 ≠ 已上架；必须经 M10 三道闸门（编译 → 模拟求值 → 人工确认）才可写 new-api。

## 2. 角色与权限

供应商：创建/编辑/暂存/提交/撤回报价单、查看本人、签署确认。
运营商务：领取/审核/驳回（必填原因）/通过、生成上传合同、发起签署、记录打款、归档。
技术运营：技术指标复核。超管：全权限。

## 3. 数据结构定义

### 3.1 报价单 Quote

`quote_id`/`quote_no`（Q{yyyyMMdd}{6位序列}）/`provider_id`/`status`/`version`（重提递增）/`currency`（USD）/`valid_from`/`valid_to`/`remark`/`reject_reason_code`/`reject_reason_text`/`submitted_at`/`reviewed_by`/`reviewed_at`/`contract_id`/审计字段。

### 3.2 明细行 QuoteItem

`item_id`/`quote_id`/`model_name`（写入 billing\_expr 的 key）/`model_alias`/`input_price`/`output_price`/`cache_read_price`（→cr）/`cache_write_price`（→cc）/`cache_write_1h_price`（→cc1h）/`image_input_price`（→img）/`audio_input_price`（→ai）/`image_output_price`（→img\_o）/`audio_output_price`（→ao）/`price_time_rules`/`price_tier_rules`/`request_rules`/`note`。
所有价格字段为真实单价 \$/1M tokens，无倍率换算。

### 3.3 时段价规则 price\_time\_rules

`tz`（IANA，默认 Asia/Shanghai）/`weekday_scope`（ALL|WEEKDAY|WEEKEND）/`peak_ranges[]`（≥1 段，start\<end，允许跨零点，段间不重叠）/`peak_multiplier`（>0）/`offpeak_multiplier`（>0）/`peak_price_override`（可选绝对值优先）。

### 3.4 阶梯价规则 price\_tier\_rules

`tier_field`（固定 len）/`tiers[]`（半开区间 (min,max]，首档 min=0，末档 max=null，label 参与档位标签）/`price_strategy`（OVERRIDE|MULTIPLY）/`tier_prices[]`（OVERRIDE 时每档 input/output，MULTIPLY 时倍率）。

### 3.5 请求级加价 request\_rules

`[{ when: "header('anthropic-beta') has 'fast-mode'", multiplier: 6 }]` → 编译为 `|||` 后缀。仅管理端高级模式开放。

### 3.6 审核记录 QuoteAudit

`audit_id`/`quote_id`/`action`（ASSIGN|TECH\_REVIEW|APPROVE|REJECT|WITHDRAW）/`operator_id`/`tech_metrics_snapshot`/`review_comment`/`before_status`/`after_status`/`created_at`。

## 4. 状态机

### 4.1 报价单状态

`DRAFT`→`SUBMITTED`→（撤回 DRAFT | `IN_REVIEW`）→（`REJECTED`→DRAFT | `APPROVED`→`CONTRACT_CREATED`）；`VOID` 作废。

状态-动作矩阵：DRAFT 可编辑/暂存/提交/作废；SUBMITTED 可撤回/作废；IN\_REVIEW 可审核；REJECTED 可编辑重提；APPROVED/CONTRACT\_CREATED 只读。

### 4.2 合同签署状态

`CREATED`→`PENDING_SIGN`→`SUPPLIER_SIGNED`→`SIGNED`→`ARCHIVED`；可 `VOIDED` 作废。

### 4.3 打款状态

`UNSETTLED`→`PAYMENT_RECORDED`→`CONFIRMED`；`VOID` 作废后重录。
**本期打款只落状态与凭证，不发起/接收任何资金。**

## 5. 校验规则汇总

### 5.1 提交时校验（M7）

V1 明细行≥1；V2 model\_name 不重复；V3 输入/输出价必填且≥0；V4 单价非负；V5 缓存价≤输入价（WARN）；V6 valid\_to>valid\_from；V7 tz 白名单；V8 时段 start\<end；V9 时段不重叠；V10 倍率>0；V11 阶梯连续无空洞；V12 首档 min=0 末档 max=null；V13 tier\_field=len；V14 OVERRIDE 每档有价；V15 request\_rules 仅管理端；V16 别名≤64；V17 模型须在检测通过清单内。

### 5.2 驳回原因码（M8）

`PRICE_TOO_HIGH`/`PRICE_STRUCTURE_INVALID`/`CACHE_PRICE_MISSING`/`TECH_RISK`/`VALIDITY_ISSUE`/`MISSING_INFO`/`OTHER`。驳回必填原因且定位到 item\_id/字段。

### 5.3 合同与打款校验（M9）

C1 仅 APPROVED 可发起合同；C2 文件 PDF/图片 ≤20MB；C3 签署需已上传盖章件；C4 金额>0 且币种一致；C5 记录打款需凭证截图；C6 归档后只读。

## 6. 异常与边界

E1 并发领取乐观锁；E2 已领取不可撤回；E3 驳回仅改备注重提允许；E4 通过后改价走新版本；E5 签署后金额变更作废合同；E6 打款凭证失败可重传；E7 有效期到期前 7 天提醒；E8 文本转义防注入；E9 跨零点时段 `hour>=22 || hour<6`；E10 时段+阶梯组合"先分档后分时段"。

## 7. 埋点

quote\_created/saved/submitted/withdrawn/assigned/rejected（带 reason\_code）/resubmitted/approved；contract\_created/signed/archived；payment\_recorded。

## 8. 验收标准

A1 多模型明细独立定价；A2 草稿无限暂存+提交全量校验；A3 时段重叠拒绝定位；A4 阶梯空洞拒绝定位；A5 tier\_field=p 拒绝；A6 撤回仅审核前；A7 驳回定位+version 递增；A8 历史对比旧值/新值/涨跌幅；A9 通过自动生成 Contract；A10 合同非法流转拒绝；A11 归档只读；A12 打款不产生资金流水；A13 全状态流转写审计。
