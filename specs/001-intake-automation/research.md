# research · 同类项目调研与决策记录

> 特性：`001-intake-automation`（进件自动化与渠道自动配置）
> 调研时间：2026-09-28｜调研方式：GitHub 仓库源码读取（`gh api`）+ 官方文档检索
> 原则：只记录**可验证事实**，每条给出仓库路径或文档 URL；推断项显式标注「推断」。

---

## 1. 调研范围

| # | 项目 | 定位 | 借鉴点 |
| --- | --- | --- | --- |
| P1 | `QuantumNous/new-api`（47k★） | one-api 主继任者，AI 模型聚合网关 | **集成目标**：渠道/定价/用量的全部集成面 |
| P2 | `songquanpeng/one-api`（31.3k★） | 上游原版，渠道模型简单 | 渠道抽象的最小集，理解字段演化起点 |
| P3 | `Veloera` / `deanxv/done-hub` / `VoAPI` | new-api 生态分支与增强版 | 渠道管理增强、批量操作 UX |
| P4 | `qixing-jk/all-api-hub`（1.4k★） | 浏览器扩展：**从凭证库一键创建自建网关渠道**、模型同步与重定向 | **最贴近本特性**：凭证 → 渠道的自动化路径 |
| P5 | `cita-777/metapi` | 元聚合层 | 多网关编排的产品形态 |
| P6 | `candies404/autodate_channel_models` | Python 工具：批量更新渠道/批量改模型列表 | **批量操作的限速与容错实践** |
| P7 | `LiteLLM`（41.8k★） | Python 网关/代理 | 模型级路由、成本追踪的数据模型 |

---

## 2. new-api 源码级事实（集成面）

以下均来自 `QuantumNous/new-api` `main` 分支源码与官方文档，标注为**可验证**。

### 2.1 建渠道支持批量模式（★ 本特性的技术前提）

`POST /api/channel/`
（文档：https://docs.newapi.ai/zh/docs/api/management/channel-management/channel-post）

请求体：

```json
{
  "mode": "single" | "batch" | "multi_to_single",
  "multi_key_mode": "<mode=multi_to_single 时必填>",
  "channel": {
    "name": "OpenAI渠道", "type": 1, "key": "<API_KEY>",
    "base_url": "https://api.openai.com",
    "models": "gpt-4,claude-3-sonnet",
    "groups": ["default"], "priority": 10, "weight": 100
  }
}
```

**结论**：`mode: "batch"` 使「一次请求建多条渠道」成为原生能力 →
「一模型一渠道」的渠道数膨胀（M 供应商 × N 模型）在**请求数**上可控。
**待实测**：`batch` 模式下 `channel` 的确切形状（单对象数组？多 `channel` 键？）——
官方文档示例只给了 `single`，见 §5 待实测项 T-1。

### 2.2 Channel 实体字段（源码 `model/channel.go`）

| 字段 | 类型 | 对本特性的用途 |
| --- | --- | --- |
| `name` | string(index) | **渠道名 = 模型名 + 供应商短码**（见 spec §3.2） |
| `key` | string(not null) | 凭证解密后写入；**日志禁止留明文** |
| `base_url` | *string | 凭证的上游地址 |
| `models` | string | 该渠道支持的模型（**一模型一渠道时为单值**） |
| `group` | string(64) | 定价分组；决定用户可用组与倍率 |
| `model_mapping` | *text | 模型名重映射（供应商模型名 ≠ 平台模型名时） |
| `priority` / `weight` | *int64 / *uint | **同模型多供应商的分流与择优杠杆**（本特性的核心调度面） |
| `auto_ban` | *int | 连续失败自动禁用 → **模型级故障自愈** |
| `status` | int | 1 启用 / 2 手动禁用 |
| `tag` | *string(index) | 按供应商打标，支持 `tag/enabled|disabled` 批量启停 |
| `setting` / `param_override` / `header_override` | *text | **模型级参数与请求头覆盖**（不同模型不同采样/超时策略） |
| `remark` | *varchar(255) | 审计备注（写入手工单号/批次） |
| `is_multi_key` / `multi_key_size` / `multi_key_mode` / `multi_key_status_list` / `multi_key_polling_index` | 多 Key 模式 | **缓解 key 副本膨胀**：一条渠道挂多 key 轮询 |

### 2.3 定价与倍率相关端点（本轮新发现，比现有基线更全）

| 端点 | 权限 | 用途 |
| --- | --- | --- |
| `GET /api/pricing` | 用户 | 对外价格表（客户端展示的模型价） |
| `GET /api/models` | 用户 | 模型目录 |
| `GET/PATCH /api/option/model_pricing` | RootAuth | **模型定价配置**（读写） |
| `POST /api/option/model_pricing/preview` | RootAuth | **定价预览**（改价前试算） |
| `POST /api/option/model_pricing/convert` | RootAuth | **定价转换**（倍率 ↔ 固定价） |
| `POST /api/option/rest_model_ratio` | RootAuth | 重置模型倍率 |
| `GET /api/ratio_config` | 限流 | 读取倍率配置 |
| `GET /api/ratio_sync/channels` | RootAuth | 可同步倍率的上游渠道列表 |
| `POST /api/ratio_sync/fetch` | RootAuth | **从上游拉取倍率**（供应商价 → 平台价的输入源） |
| `POST /api/channel/fetch_models` | 管理 | 从上游拉模型清单（建渠道前预览，可替代 `sync_upstream`） |
| `POST /api/channel/:id/key` | 管理 | 更新渠道 key（**轮换与批量改 key 的入口**） |
| `POST /api/channel/status/batch`、`/api/channel/tag/enabled|disabled` | 管理 | 批量启停 |

**推断（标注）**：`/api/option/model_pricing` 族的存在说明 new-api 已把「模型定价」提升为一等配置对象，
其 `convert` 语义大概率是「倍率制 ↔ 每 1M token 固定价制」互转 —— 与现有设计「写
`billing_setting.billing_expr`」可能是**两条并存路径**。二者关系需实测确认（§5 T-2）。

### 2.4 既有基线文档已确认的能力（沿用，不重复验证）

`03-new-api_能力基线.md` 的 F1–F8：计费表达式系统（`hour/weekday/len/cr/cc/cc1h`）、
`billing_setting.billing_expr` 按模型存储、用量表 `Log` 的渠道维度、**F8 缺口**（`Log` 无独立
cache token 字段，在 `Other` JSON 内）。本特性**不推翻**这些结论。

---

## 3. 同类项目对我们的启示

| 来源 | 实践 | 我们的采纳 |
| --- | --- | --- |
| new-api 官方渠道管理 UI | 批量启用/禁用/打标签；「测试所有渠道」一键批测 | 管理端「自动配置控制台」提供等价批量操作 + **批量回读校验** |
| `all-api-hub` | 从「凭证库」一键创建网关渠道，凭证 → 渠道的映射自动化 | 进件流水线的最后一公里（凭证 → 渠道）我们已内建，补**一键重配**（凭证更新后重建渠道） |
| `autodate_channel_models` | 批量操作加**随机延时**避免压垮 API；分批处理 + 统计 | 渠道批量写入必须**限速 + 分批 + 断点续传**（写进 plan §4） |
| `LiteLLM` | 模型级路由与成本追踪分离（`model → deployment` 多对多） | 印证「一模型多渠道」是行业通用做法：我们的渠道 = 「模型 × 供应商」最小可调度单元 |
| `Veloera`/`done-hub` | 渠道管理 UX 增强（筛选、标签、批量） | 管理端「渠道价格表」做成**矩阵视图**（模型 × 供应商）而非平铺列表 |
| `metapi` | 元聚合层：多个网关作为上游 | **超越本特性范围**，记为演进方向（Out of Scope O-8） |

---

## 4. 决策记录（DR）

| 编号 | 决策 | 理由 | 状态 |
| --- | --- | --- | --- |
| DR-01 | 渠道粒度 = **模型 × 供应商**（一模型一渠道） | 使 new-api 的 `priority/weight/auto_ban/param_override` 从供应商级提升为**模型级**调度杠杆；同模型多供应商可分流择优；故障隔离粒度更细 | 采纳 |
| DR-02 | 渠道名 = `AAP-{short_code}-{model_slug}` | 可读、可反解（解析出供应商与模型）、天然唯一；`/` 等非法字符转 `_`；满足「模型名 + 渠道名」 | 采纳 |
| DR-03 | 保留「合并渠道」模式为**可配策略**（`channel_granularity: PER_MODEL \| PER_PROVIDER`） | 长尾模型拆渠道收益低于成本（渠道数膨胀、key 副本、管理开销）；策略化可平滑演进，且不破坏既有实现 | 采纳 |
| DR-04 | 渠道批量创建走 **`mode: "batch"`**；失败按**单模型**回滚 | 单模型回滚比供应商级整批回滚代价更低（新粒度带来的直接收益） | 采纳（待 T-1 实测确认 payload） |
| DR-05 | 新建**两张价格表**：模型价格表（平台基准/对外价）+ 渠道价格表（采购成本/结算基准） | 两个视角共同构成毛利视图与对账基准；现有 `aap_reference_price` 只是原料，没有视图与流程 | 采纳 |
| DR-06 | key 副本问题优先用 new-api **多 Key 模式**（`multi_to_single`）缓解，而非自建 key 池 | 不改造 new-api 的前提下，这是最小的重复面；且轮换入口 `POST /api/channel/:id/key` 已存在 | 采纳（待 T-3 评估） |
| DR-07 | 自动化采用**四级（L0–L3）+ 风险矩阵**，不默认全自动 | 一票否决、凭证安全、资金相关动作不能无人值守；但低风险模型/白名单供应商可全自动以达成「系统侧 ≤2 小时」的北极星 | 采纳 |
| DR-08 | 契约仍以 `tools/gen-backend-models.py` 为唯一真源；`specs/**/contracts/` 只登记**规格意图** | 避免双真源；生成器已驱动 108 端点 + openapi + json-schema + 门禁测试 | 采纳 |
| DR-09 | 批量写入限速：默认 **≤5 req/s**、分批 ≤20 条、失败退避 30s/2m/10m | 借鉴 `autodate_channel_models` 的延时实践 + 现有 R-13（RPM 硬上限 60）的保守推论 | 采纳 |

---

## 5. 待实测项（实现前必须实测，禁止臆测）

| # | 待确认 | 影响 | 验证方式 |
| --- | --- | --- | --- |
| T-1 | `mode: "batch"` 的请求体确切形状与响应（返回创建的 id 列表？部分失败如何表达？） | 批量建渠道的实现与部分失败处理 | 对本地 new-api 桩/真实实例发一次 batch 请求，记录原始响应 |
| T-2 | `/api/option/model_pricing` 与 `billing_setting.billing_expr` 的关系（并存还是替代） | 定价写入路径选择 | 读 `controller/option.go` + 实测 PATCH 后读回 |
| T-3 | 多 Key 模式下 `multi_key_mode` 的取值与轮询语义；key 更新是否影响已在跑的请求 | DR-06 的可行性 | 源码 `constant.MultiKeyMode` + 实测 |
| T-4 | 渠道 `name` 长度上限与字符集限制（模型名可能很长/含特殊字符） | 命名规则 DR-02 的边界 | 实测超长/特殊字符写入 |
| T-5 | 单位模型渠道的调度开销（渠道数 M×N 到千级时 new-api 的路由与列表性能） | 是否需要对长尾模型合并（DR-03 阈值） | 压测：造 500/1000 条渠道，测路由 P95 与列表加载 |

> 未决项一律以本节为准；在 T-1/T-2 实测前，**不得**把相应实现写成「已定」。

---

## 6. 参考来源

- new-api 仓库：https://github.com/QuantumNous/new-api
- 新建渠道 API 文档：https://docs.newapi.ai/zh/docs/api/management/channel-management/channel-post
- 渠道管理模块文档：https://doc.newapi.pro/api/fei-channel-management/
- 渠道管理功能指南：https://www.newapi.ai/zh/docs/guide/feature-guide/admin/channel
- one-api：https://github.com/songquanpeng/one-api
- all-api-hub：https://github.com/qixing-jk/all-api-hub
- autodate_channel_models：https://github.com/candies404/autodate_channel_models
- LiteLLM：https://github.com/BerriAI/litellm
- SDD 结构参考（Spec Kit）：`.specify/memory/constitution.md` + `specs/NNN-*/{spec,plan,tasks,research,data-model,contracts,quickstart}`
