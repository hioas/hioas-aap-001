# 全流程自驱测试 · 首轮根因（2026-10-15）

## 结果：33 项 / 通过 5 / 失败 28（报告 `.agents/state/evidence/e2e-run-20260929.json`）

## 根因：`app.credential.allow-loopback` 未开启（测试环境漏配，非代码缺陷）

**第一个失败**就是 P1「`POST /credentials`（上游=`http://127.0.0.1:9911/v1`）」，
其后 P5 `KeyError: 'contract_id'`、P8 `E-1201`、P10 `E-1601` 等**全部是它的下游效应**。

证据链：
1. `aap-server/src/main/java/com/hioas/aap/common/OutboundUrlGuard.java:33`
   `OutboundUrlGuard(@Value("${app.credential.allow-loopback:false}") boolean allowLoopback)`
   → **默认 false**；
2. 同文件 `:23-24` 注释自述：「`app.credential.allow-loopback`（默认 false）仅用于本地端到端
   联调与测试：放行 127.0.0.1/::1，**不放行**私网、链路本地与元数据地址（AC-29 仍可验证）」；
3. `application.yml` 中**没有**该配置项（rg 无命中）；
4. `/e/env/aap-server.env` 中**没有**对应变量（键名清单：AAP_CREDENTIAL_AES_KEY / AAP_JWT_SECRET /
   AAP_SMS_EXPOSE_CODE / DB_* / LOG_DIR / SERVER_PORT / DB_TEST_NAME）。

**这是正确的安全设计**：SSRF 防护默认拒绝回环地址，只有显式开关才放行，且放行范围仅回环
（私网/元数据仍拒绝，AC-29 可继续验证）。因此本项判为**测试环境配置缺失**，不改代码。

## 处置

- 复现方式：`APP_CREDENTIAL_ALLOW_LOOPBACK=true` 随进程启动（Spring relaxed binding）；
- 重启命令：`bash tools/with-env.sh aap-server bash -c 'cd aap-server && SERVER_PORT=8086 \
  APP_CREDENTIAL_ALLOW_LOOPBACK=true mvn -B -ntp spring-boot:run'`
- 重跑报告：`.agents/state/evidence/e2e-run-20261015-b.json`

## 顺带确认（对 APPLY 执行器有意义）

- 桩 `9911` 存活：`/api/channel/` 返回 401（需 API key，正常）—— 说明桩在跑；
- 后端 `8086` 首轮启动成功（管理端 vite 构建 2m21s → H5 uni build → Spring Boot），
  说明**新代码（APPLY 执行器 + api_key_cipher 修复）已编译进运行实例**。

## 待办（本轮未完成）

- [ ] 重跑读数（进行中）
- [ ] 通过后补跑新的 APPLY 链路（建批次 mode=APPLY → 真实下发 → 回读）
