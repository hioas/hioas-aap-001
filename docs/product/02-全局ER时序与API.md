# 02 · 全局 ER 模型 · 核心时序 · API 增量

> 对象域设计的核心：**每域单一写入口，跨域只读**。
> 现状：59 张表、117 个端点（`docs/backend/endpoints.json` 为冻结契约）。

## 1. 全局对象域视图

```mermaid
flowchart LR
  subgraph IAM[身份域]
    AU[aap_admin_user]
    PA[aap_provider_account]
    TK[aap_auth_token]
  end
  subgraph SUPPLY[供给域]
    PV[aap_provider]
    CR[aap_credential]
    DJ[aap_detection_job]
    SU[aap_supply_unit]
  end
  subgraph CATALOG[商品域]
    VD[aap_vendor]
    MD[aap_model]
    MP[aap_model_price 新]
    CP[aap_channel_price 新]
    RP[aap_reference_price]
  end
  subgraph TRADE[交易域]
    QT[aap_quote]
    CT[aap_contract]
    PAY[aap_payment]
    ST[aap_settlement]
  end
  subgraph ORCH[编排域]
    CB[aap_channel_binding]
    CMP[aap_compilation]
    SY[aap_sync_task]
    BAT[aap_config_batch 新]
  end
  subgraph METER[计量域]
    UB[aap_usage_hourly]
    UL[aap_settlement_line]
  end
  subgraph GOV[治理域]
    AL[aap_audit_log]
  end

  PV --> PA
  PV --> CR
  PV --> SU
  CR --> DJ
  DJ --> SU
  SU --> CB
  MD --> MP
  SU --> CP
  MP --> CP
  SU --> QT
  QT --> CT
  CT --> PAY
  CT --> ST
  CB --> SY
  CMP --> SY
  BAT --> CB
  SY --> UB
  UB --> ST
  ST --> UL
```

## 2. 关键实体与不变量

| 域 | 实体 | 主键/唯一 | 关键不变量 |
|---|---|---|---|
| 供给 | `aap_provider` | USCC 唯一 | 状态机 DRAFT→…→PUBLISHED；PUBLISHED 才可上架 |
| 供给 | `aap_credential` | `(provider_id, api_key_fingerprint)` 唯一 | key 只存密文+指纹+掩码；`detection_status='PASS'` 才可用于生产路由 |
| 供给 | `aap_supply_unit` | `(provider_id, model_name)` 唯一 | **= 模型 × 供应商**；是「一模型一渠道」的聚合根；`granularity` 决定单模型/合并 |
| 商品 | `aap_model_price` **新** | `(model_id, version)` 唯一 | **只增不改**；对外价变更生成新版本；历史账单引用旧版本 |
| 商品 | `aap_channel_price` **新** | `(supply_unit_id, effective_from)` 唯一 | 采购价必须可回溯到 `quote_id` 或 `contract_id` |
| 编排 | `aap_channel_binding` | `(supply_unit_id)` 唯一（PER_MODEL） | `channel_name` = `AAP-{short_code}-{model}`，≤64 字符，可反解 |
| 编排 | `aap_config_batch` **新** | `batch_no` 唯一 | dry-run 必须零上游写入；apply 必须逐项独立提交 |
| 编排 | `aap_config_batch_item` **新** | `idempotency_key` 唯一 | 单项失败不回滚已成功项（R-59） |
| 交易 | `aap_settlement` | `(provider_id, statement_month)` 唯一 | 同周期幂等；无用量不出空单；出账后终态 |
| 计量 | `aap_usage_hourly` | `(provider_id, channel_id, model_name, stat_hour)` 唯一 | 归集幂等，可重跑 |

## 3. 核心时序（4 个关键流程）

### 3.1 进件到上架（主链路）

```mermaid
sequenceDiagram
  participant P as 供应商
  participant API as aap-server
  participant DET as 检测引擎
  participant OPS as 技术运营
  participant GW as 网关(new-api)

  P->>API: 提交凭证 (CRED-01)
  API->>API: 加密存储 + 指纹去重
  P->>API: 预检 (CRED-05)
  API->>GW: 真实探活
  GW-->>API: 连通/鉴权/限流
  P->>API: 发起检测 (DET-01)
  API->>DET: D1–D8 打分
  DET-->>API: 分数 + 置信度
  alt 检测 PASS 或 人工放行(DET-06)
    P->>API: 提交报价 (QT-02)
    OPS->>API: 审核 (ADM-R03)
    OPS->>API: 合同签发 (ADM-CT02)
    P->>API: 签署 (CON-04 SEAL)
    OPS->>API: 确认 (ADM-CT03)
    OPS->>API: 编译 (ADM-Q01)
    OPS->>API: 模拟验证 (ADM-CP03)
    OPS->>API: 人工确认闸门③ (ADM-CP04)
    OPS->>API: 上架同步 (ADM-S09 三段式)
    API->>GW: POST /api/channel/
    API->>GW: GET /api/channel/{id} 回读
    API-->>OPS: SYNCED + 回读一致
  else 检测未通过
    API-->>P: 整改清单 + 复检入口
  end
```

### 3.2 批量配置（dry-run → apply）

```mermaid
sequenceDiagram
  participant OPS as 技术运营
  participant API as aap-server
  participant PL as ChannelConfigPlanner
  participant GW as 网关

  OPS->>API: POST /admin/config-batches {mode:DRY_RUN}
  API->>PL: 展开 + 差异计算
  PL-->>API: CREATE/UPDATE/SKIP/DISABLE
  API-->>OPS: 批次(SUCCEEDED) + 差异清单（零写入）
  OPS->>API: POST /admin/config-batches {mode:APPLY}
  loop 每条明细（≤5 req/s）
    API->>GW: POST /api/channel/
    API->>GW: GET /api/channel/{id}
    API->>API: ReadbackComparator 判定
    Note over API: SUCCEEDED / MISMATCH / FAILED（逐项提交）
  end
  API-->>OPS: 批次 PARTIAL/SUCCEEDED + mismatch_count
```

### 3.3 结算出账

```mermaid
sequenceDiagram
  participant OPS as 运营
  participant API as aap-server
  participant P as 供应商

  OPS->>API: POST /admin/settlements (ADM-PAY06)
  API->>API: 取周期用量（渠道×模型）
  alt 无用量
    API-->>OPS: 409 E-1601（不出空单）
  else 有用量
    API->>API: 总额 Σ明细；平台费=合同费率×基数；净额=总额−平台费
    API-->>OPS: DRAFT 结算单
    OPS->>API: 确认出账 (ADM-PAY08)
    API-->>OPS: CONFIRMED（终态）
    P->>API: 读结算单 (SET-01/02)
    API-->>P: 只读视图（越权/不存在同 404）
  end
```

### 3.4 价格变更（版本化）

```mermaid
sequenceDiagram
  participant OPS as 运营
  participant API as aap-server
  participant CAL as 商品域
  participant SET as 结算

  OPS->>API: 调整对外价
  API->>CAL: 新建 model_price 版本(v+1)
  CAL-->>API: 新版本生效时间
  Note over SET: 历史结算单仍引用旧版本（只增不改）
  OPS->>API: 触发渠道价差同步
  API->>CAL: 新建 channel_price（effective_from）
```

## 4. API 增量（按域，均需先改生成器再重生成）

| 域 | 端点 | 方法 | 说明 | 状态 |
|---|---|---|---|---|
| 供给 | `/admin/supply-units` | GET | 供给单元列表（供应商/模型/状态） | ✅ 已有 |
| 供给 | `/admin/supply-units/{id}` | GET | 详情 | ✅ |
| 供给 | `/admin/supply-units/{id}/reconfigure` | POST | 重配置（默认 dry-run） | ✅ |
| 供给 | `/admin/supply-units/{id}/offline` | POST | 下线 | ✅ |
| 编排 | `/admin/config-batches` | POST/GET | 批次创建/列表 | ✅ |
| 编排 | `/admin/config-batches/{id}` | GET | 详情（含明细与 mismatch） | ✅ |
| 编排 | `/admin/config-batches/{id}/items/{itemId}/retry` | POST | 单模型重试 | ✅ |
| 编排 | `/admin/config-batches/{id}/items/{itemId}/rollback` | POST | 单模型回滚 | ✅ |
| 商品 | `/admin/model-prices` | GET/POST | 模型价格（版本化） | 🆕 待加 |
| 商品 | `/admin/model-prices/{modelId}/versions` | GET | 价格版本历史 | 🆕 |
| 商品 | `/admin/channel-prices` | GET/POST | 渠道价格（采购视角） | 🆕 |
| 商品 | `/admin/pricing/matrix` | GET | 比价矩阵 | 🆕 |
| 商品 | `/admin/pricing/margin` | GET | 毛利视图 | 🆕 |
| 商品 | `/admin/pricing/coverage` | GET | 供给覆盖（断供风险） | 🆕 |
| 进件 | `/admin/intake/policies` | GET/PUT | L0–L3 分级策略 | 🆕 |
| 进件 | `/admin/intake/tasks/{id}/approve` | POST | 人工放行/驳回 | 🆕 |
| 客户端 | `/client/models` | GET | 模型浏览（对外价） | 🆕 |
| 客户端 | `/client/keys` | GET/POST/DELETE | API Key 自助 | 🆕 |
| 客户端 | `/client/usage` | GET | 用量/账单 | 🆕 |
| 客户端 | `/client/invoices` | GET | 发票/合同下载 | 🆕 |

**新增表（P2 规划）**：`aap_model_price`、`aap_channel_price`、`aap_intake_policy`、`aap_client_account`、`aap_client_key`（V17+）。迁移需同步 `MigrationTest` 与 ER 文档（双向门禁）。

## 5. 域间契约（防跨域写）

| 调用方 | 被调方 | 允许方式 | 禁止 |
|---|---|---|---|
| 编排域 | 商品域 | 只读价格（当前生效版本） | 直接改价格表 |
| 计量域 | 编排域 | 只读渠道/模型映射 | 改绑定 |
| 交易域 | 计量域 | 只读用量聚合 | 改用量原始数据 |
| 客户端 | 编排域 | ❌ 不直连 | 暴露 channel_id / 成本价 |
| 所有域 | 治理域 | 只写审计 | 跳过审计 |

## 6. 与现状的差异（需在 P5 原型中体现）

1. **价格双轨**：现有只有 `aap_reference_price`（参考价），缺「平台对外价（版本化）」与「采购价（可回溯合同）」。
2. **编排可观测**：现有同步任务有，但缺**批量差异预演**的运营界面（后端已就绪）。
3. **客户端缺失**：整个需求侧（模型浏览/Key/账单）尚无端点与界面。
4. **进件分级缺失**：L0–L3 只有规格，无策略配置与审批界面。
