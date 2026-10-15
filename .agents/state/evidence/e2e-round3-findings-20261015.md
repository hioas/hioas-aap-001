# 全流程自驱测试 · 第 3 轮读数 + 两条必须记住的坑（2026-10-15）

## 读数（报告 `.agents/state/evidence/e2e-run-20261015-c.json`）

| 轮次 | 通过/总计 | 首个失败点 | 根因 |
|---|---|---|---|
| 1 | **5 / 33** | P1 登记凭证 | `app.credential.allow-loopback` 未开 → SSRF 防护拒绝 `127.0.0.1` |
| 3 | **14 / 33** | P6 记录打款（ADM-PAY04） | 待查（本轮未定位） |

第 3 轮证明 `allow-loopback` 修复有效：P0 认证 → P1 凭证 → 检测 → 报价 → 审核 → 合同全部通过，
失败自 **P6「记录打款（带凭证文件）」** 起级联（`payment_id` 缺失 → 后续全部拿不到 ID）。

## 坑 1（我犯的误判，代价：杀掉了一个健康的后端）：`curl` 走了系统代理

**现象**：`curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8086/actuator/health` 返回 **502**，
据此判定「后端没起来」；而同一时刻该后端**正在正常处理端到端请求**
（日志可见 `合同签发 contract_no=HT202610150015`、`CONTRACT_SIGN` 审计）。

**原因**：本机配了系统代理，`curl` 默认走代理；而 Python `requests` 脚本直连正常。

**正确做法**：
- 探测本机服务一律加 `--noproxy '*'`：`curl --noproxy '*' -s -o /dev/null -w '%{http_code}' ...`
- 更可靠：直接看后端日志判断存活，不要只信 `curl` 的码
- `502`（Bad Gateway）**不等于**服务未启动——它往往是代理层产生，不是目标服务的真实状态

## 坑 2：后端启动成本极高，必须跳过前端构建

`aap-server/pom.xml` 把 `build-admin` / `build-h5` 挂在 `generate-resources` 阶段用 `cmd` 跑 npm 构建，
**无条件执行、无 skip 属性** → 每次启动都要重建管理端 + H5。

- 不带开关：实测 **17:01 min**（"第二次启动 6 分钟还在 vite build" 同源）
- 带 `-Dexec.skip=true`：**2:58 min**（约 6 倍加速）

**规则：验证后端改动时一律加 `-Dexec.skip=true`**（纯启动参数，不需要改 pom）。

## 待办

- [ ] 定位 P6「记录打款（ADM-PAY04，带凭证文件）」失败根因（报告未记错误详情，需重跑并抓原始响应）
- [ ] 全绿后补跑新的 APPLY 链路（`mode=APPLY` → 真实下发 → 回读）
- [ ] `pom.xml` 的前端构建应改为 profile / 独立 phase（他方在制品，只报告不擅改）
