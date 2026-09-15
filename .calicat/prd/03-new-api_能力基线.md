# new-api 能力基线

# new-api 能力基线（技术事实层）

> 本产品的最后一公里是把供应商报价"写进 new-api"。因此 new-api 支持什么、不支持什么，直接决定本产品的功能边界。
> 本文只记录可验证的代码事实，每条链向仓库路径+行号。

## 1. 结论速览（决定产品能力的 7 条硬事实）

| #  | 事实                                                                                                                                             | 对本产品的意义                             |
| -- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| F1 | 渠道表 Channel 含 name/key/base\_url/models/group/model\_mapping/priority/weight/setting/tag/remark/status 等 25+ 字段                                | 供应商提交的测试凭证可直接映射为一条渠道记录，无需扩展 new-api |
| F2 | 计费表达式系统 pkg/billingexpr 原生支持 hour(tz) / weekday(tz)                                                                                            | 峰谷价可自动编译，无需改造 new-api               |
| F3 | 支持 len 阶梯条件                                                                                                                                    | 阶梯价可自动编译                            |
| F4 | 支持 cr/cc/cc1h（缓存读/写/1h 写）独立计价变量                                                                                                                | 缓存价可自动编译，且有自动排除机制避免重复计费             |
| F5 | 表达式按模型存于 billing\_setting.billing\_expr（option 表 JSON）                                                                                         | 同步接口 = 写 option，路径清晰                |
| F6 | 已有 POST /api/channel/(AddChannel) / PUT /api/channel/(UpdateChannel) 及 POST /api/models/sync\_upstream                                         | 上架是调用既有管理 API，不需改 new-api 代码        |
| F7 | model.Log 表有 channel\_id / model\_name / created\_at / prompt\_tokens / completion\_tokens / quota，且 SumUsedQuota(... channel int ...) 支持按渠道聚合 | 按渠道×模型×小时的用量统计可直接算                  |

> ⚠️ **F8（缺口）**：`Log` 表没有独立的缓存命中 token 字段（cache token 落在 `Log.Other` JSON 内）。
> → 影响："缓存命中用量统计"需解析 `other`，或改从表达式求值结果侧采集。

## 2. 关键证据明细

### 2.1 渠道实体（F1）

`Channel` 结构体含 25+ 字段，供应商提交的测试凭证三要素（Key/BaseURL/Models）可直接映射。其余字段（Group/Priority/Weight/Tag/Setting 等）由 AAP 按规则填充。供应商侧只填 Key/BaseURL/Models 三项。

### 2.2 计费表达式系统（F2–F5）—— 技术支点

**支持的变量**：

* 输入：`p`（输入 token，计价用）、`len`（上下文总长度，条件判断用）、`cr`（缓存读）、`cc`/`cc1h`（缓存创建）、`img`/`ai`（图片/音频）
* 输出：`c`（输出）、`img_o`/`ao`（图片/音频输出）

**内置函数**：`hour(tz)`、`minute(tz)`、`weekday(tz)`、`month/day(tz)`、`tier(name, value)`、`param(path)`、`header(key)`、`max/min/abs/ceil/floor`、`len(tz)`

**官方示例**：

```
# Simple flat pricing
tier("base", p * 2.5 + c * 15 + cr * 0.25)

# Multi-tier — use len for tier conditions
len <= 200000
  ? tier("standard", p * 3 + c * 15 + cr * 0.3 + cc * 3.75 + cc1h * 6)
  : tier("long_context", p * 6 + c * 22.5 + cr * 0.6 + cc * 7.5 + cc1h * 12)
```

**重要机制**：

* 价格是真实价格——表达式系数是供应商公布的 \$/1M tokens 真实单价，不是倍率。
* `p`/`c` 自动排除——表达式里用了 `cr`，则 cache token 从 `p` 扣掉单独计费，避免重复计费。
* 阶梯条件必须用 `len` 而非 `p`——否则缓存命中导致 `p` 变小会误判档位。
* 请求级条件用 `|||` 追加。
* 表达式带 `v1:` 版本前缀。

**存储（F5）**：`billing_setting.billing_expr`（option 表 JSON，key = 模型名）。同步路径 = AAP 编译表达式 → 写 option。

### 2.3 管理 API（F6）

* `POST /api/channel/`（AddChannel）★上架
* `PUT /api/channel/`（UpdateChannel）★改价
* `POST /api/channel/status/batch`、`POST /api/channel/:id/status`（启停）
* `POST /api/channel/tag/enabled` / `tag/disabled`（按供应商打标批量启停）
* `POST /api/models/sync_upstream`（从上游同步模型清单）
* 认证要点：渠道写操作需要 AdminAuth + 细粒度权限（`ChannelSensitiveWrite`/`ChannelWrite`）；AAP 需要专用最小权限账号。

### 2.4 用量数据源（F7 / F8）

`Log` 表含 `CreatedAt`（unix 秒）、`ModelName`、`ChannelId`、`PromptTokens`、`CompletionTokens`、`Quota` 等。`SumUsedQuota(... channel int ...)` 已带 channel 维度，按小时切窗口即可实现"每小时×每渠道×每模型"统计。

**缺口 F8**：`Log` 表无 `cache_read_tokens` 字段，缓存命中量需方案 C（AAP 自建用量表，按小时拉日志并落库，含缓存字段）。

## 3. 对 AAP 的边界结论

| 能力            | 结论     | 依据                                                   |
| ------------- | ------ | ---------------------------------------------------- |
| 自动建渠道         | ✅ 可直接做 | POST /api/channel/                                   |
| 自动改价          | ✅ 可直接做 | 写 billing\_setting.billing\_expr + PUT /api/channel/ |
| 峰谷价           | ✅ 可直接做 | hour(tz)                                             |
| 阶梯价           | ✅ 可直接做 | len 条件 + tier()                                      |
| 缓存价           | ✅ 可直接做 | cr/cc/cc1h                                           |
| 按供应商批量启停      | ✅ 可直接做 | tag/enabled、tag/disabled                             |
| 上游模型清单同步      | ✅ 可直接做 | POST /api/models/sync\_upstream                      |
| 按渠道×模型×小时用量   | ✅ 可做   | SumUsedQuota(channel,…) + 时间窗                        |
| 缓存命中用量        | ⚠️ 需调整 | Log 表无独立字段，见 F8                                      |
| 改造 new-api 源码 | ❌ 不需要  | 全部通过既有管理 API 完成                                      |

> 最重要的可行性结论：AAP 可以作为外挂系统存在，通过 new-api 既有管理 API 完成全部集成，new-api 侧零代码改动。
