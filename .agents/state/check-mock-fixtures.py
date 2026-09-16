#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测量面 mock fixture 体检：证明「页面会调用的 GET 路径」在 serve.py 下真的能取到数。

为什么需要它：mock 目录是「同名文件」映射，缺一个文件不会报错，只会让被测页面在 430 宽实测里
静默走 404 分支（serve.py 返回 {"code":"E-2001"}）→ 实测数字就失去意义。本轮的真实缺口：
序号 9「保存并继续」落到 /pages/model-pricing/index?quoteId=q9，该页 onMounted 用
src/api/quote.ts 的 listItems() 回落取首行 → GET /api/v1/quotes/q9/items，而 api/ 目录里
只有 q9/items/post，没有 index → 404（红基线）。

用法：
  python .agents/state/check-mock-fixtures.py            # 检查全部 CHECKS
  python .agents/state/check-mock-fixtures.py --mock api # 只检查某个 mock 目录

退出码 0 = 全部 PASS；1 = 有 FAIL（列出路径 + 原因）。
脚本自己拉起 serve.py（独立端口）并用 http.client 直接请求，不依赖外部服务。
"""
import http.client
import io
import json
import os
import socket
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MOCK_ROOT = os.path.join(ROOT, ".agents", "state", "h5-measure")
PAGES = os.path.join(ROOT, "aap-client", "dist", "build", "h5")

# 被检查的 GET 路径：每条都注明「谁在调 + 依据」，「must」是该页渲染必需的最小键。
CHECKS = [
    {
        "mock": "api",
        "method": "GET",
        "path": "/api/v1/quotes/q9/items",
        "why": "序号 9 保存并继续 → /pages/model-pricing/index?quoteId=q9 的回落入口（src/api/quote.ts listItems）",
        "must": [],
        "check": lambda d: isinstance(d.get("items"), list) and len(d["items"]) > 0
        and d["items"][0].get("model_name"),
    },
    {
        "mock": "api",
        "method": "GET",
        "path": "/api/v1/quotes",
        "why": "序号 8 报价单列表（quoteApi.list）",
        "must": ["items"],
        "check": None,
    },
    {
        "mock": "api",
        "method": "GET",
        "path": "/api/v1/credentials",
        "why": "序号 3/4/9 凭证列表（credentialApi.list）",
        "must": ["items"],
        "check": None,
    },
    {
        "mock": "api",
        "method": "GET",
        "path": "/api/v1/usage/summary",
        "why": "序号 2 工作台 / 序号 22 用量概览（usageApi.summary）",
        "must": [],
        "check": None,
    },
    {
        "mock": "api",
        "method": "GET",
        "path": "/api/v1/provider/profile",
        "why": "序号 2 工作台企业信息 / 序号 23 账号信息（providerApi.profile）",
        "must": [],
        "check": None,
    },
    {
        "mock": "api",
        "method": "POST",
        "path": "/api/v1/auth/sms/send",
        "why": "序号 1 登录注册「获取验证码」（src/api/auth.ts sendSms）",
        "must": ["ttl"],
        "check": None,
    },
    {
        "mock": "api",
        "method": "POST",
        "path": "/api/v1/auth/sms/login",
        "why": "序号 1 登录注册「登录 / 注册」（src/api/auth.ts login；无 token → afterLogin 写空 token）",
        "must": ["token", "role"],
        "check": lambda d: bool(d.get("token")),
    },
    {
        "mock": "api",
        "method": "POST",
        "path": "/api/v1/provider/qualifications",
        "why": "序号 4-v1 接入凭证-表单「提交接入」（src/api/access-application.ts submit；缺 fixture 则 404 → 提交后停在原页 + 错误 toast）",
        "must": ["id", "detection_job_id"],
        "check": lambda d: bool(d.get("detection_job_id")),
    },
    {
        "mock": "api-11",
        "method": "GET",
        "path": "/api/v1/quotes/items/qi1",
        "why": "序号 11 模型定价详情（quoteApi.getItem）",
        "must": ["model_name", "input_price", "output_price"],
        "check": None,
    },
    {
        "mock": "api-12-v2",
        "method": "GET",
        "path": "/api/v1/credentials",
        "why": "序号 12-v2 新增报价单-APIKey 下拉展开首屏（credentialApi.list → 三个候选项）",
        "must": ["items"],
        "check": lambda d: isinstance(d.get("items"), list) and len(d["items"]) == 3
        and bool(d["items"][0].get("api_key_mask")),
    },
    {
        "mock": "api-12-v2",
        "method": "GET",
        "path": "/api/v1/credentials/c2",
        "why": "序号 12-v2 下拉选中项（credentialApi.get → 带出模型清单；缺 fixture 则面板选不中）",
        "must": ["model_list"],
        "check": lambda d: isinstance(d.get("model_list"), list) and len(d["model_list"]) > 0
        and d["model_list"][0].get("model_name"),
    },
    {
        "mock": "api-12-v2",
        "method": "POST",
        "path": "/api/v1/quotes",
        "why": "序号 12-v2「保存并继续」（quoteApi.create；缺 fixture 则 404 → 停在原页 + 错误 toast）",
        "must": ["quote_id"],
        "check": lambda d: bool(d.get("quote_id")),
    },
    {
        "mock": "api-12-v2",
        "method": "POST",
        "path": "/api/v1/quotes/q9/items",
        "why": "序号 12-v2「保存并继续」逐模型明细（quoteApi.saveItems）",
        "must": [],
        "check": lambda d: d.get("ok") is True,
    },
    {
        "mock": "api-12-v2",
        "method": "GET",
        "path": "/api/v1/quotes/q9/items",
        "why": "序号 12-v2 保存成功后的落地页 /pages/model-pricing/index?quoteId=q9 回落取数",
        "must": ["items"],
        "check": None,
    },
    {
        "mock": "api-12-v2",
        "method": "GET",
        "path": "/api/v1/auth/me",
        "why": "序号 12-v2 面板底部操作「前往「我的设置」新建凭证」的落地页 /pages/settings/index（authApi.me）",
        "must": ["phone"],
        "check": lambda d: bool(d.get("phone")),
    },
    {
        "mock": "api-12-v3",
        "method": "GET",
        "path": "/api/v1/quotes/q9",
        "why": "序号 12-v3 保存成功页首屏（quoteApi.detail → 单号/名称/状态/明细行）",
        "must": ["quote_no", "credential_id"],
        "check": lambda d: bool(d.get("quote_no")) and bool(d.get("credential_id")),
    },
    {
        "mock": "api-12-v3",
        "method": "GET",
        "path": "/api/v1/credentials/c1",
        "why": "序号 12-v3 按 credential_id 带出模型清单（设计「共 5 个 / 勾选 3 个」= 5 项 3 选中）",
        "must": ["model_list", "env_tag", "api_key_mask"],
        "check": lambda d: isinstance(d.get("model_list"), list) and len(d["model_list"]) == 5
        and sum(1 for m in d["model_list"] if m.get("selected")) == 3,
    },
    {
        "mock": "api-12-v3",
        "method": "GET",
        "path": "/api/v1/quotes/q9/items",
        "why": "序号 12-v3「继续设置模型报价」的落地页 /pages/model-pricing/index?quoteId=q9 回落取数（缺则落地页 404 且错误 toast 盖住出口证据）",
        "must": ["items"],
        "check": lambda d: isinstance(d.get("items"), list) and len(d["items"]) > 0,
    },
    {
        "mock": "api-12-v3",
        "method": "GET",
        "path": "/api/v1/quotes",
        "why": "序号 12-v3「返回报价单列表 / 关闭」的落地页 /pages/quotes/index 取数（缺则落地页弹「数据加载失败」）",
        "must": ["items"],
        "check": lambda d: isinstance(d.get("items"), list) and len(d["items"]) > 0,
    },
    {
        "mock": "api-15",
        "method": "GET",
        "path": "/api/v1/contracts/c1",
        "why": "序号 15 合同签署页取数 /pages/contract/index（contractApi.detail；缺则整页空态 + 错误 toast）",
        "must": ["contract_no", "title"],
        "check": lambda d: bool(d.get("contract_no")) and bool(d.get("title")),
    },
    {
        "mock": "api-15",
        "method": "GET",
        "path": "/api/v1/contracts/c1/file",
        "why": "序号 15「下载 PDF」先按 /contracts/{id}/file 取地址再 uni.downloadFile（缺则只 toast 不下载）",
        "must": ["url"],
        "check": lambda d: bool(d.get("url")),
    },
    {
        "mock": "api-15",
        "method": "POST",
        "path": "/api/v1/contracts/c1/sign",
        "why": "序号 15「去签署」二次确认后发起签署（缺则 serve 对未定义 POST 兜底假成功，签署结果不可辨）",
        "must": ["status"],
        "check": lambda d: bool(d.get("status")),
    },
    {
        "mock": "api-20",
        "method": "GET",
        "path": "/api/v1/notifications?page=1&pageSize=20",
        "why": "序号 20 站内信列表取数 /pages/messages/index（缺则整页空态 + 错误 toast）",
        "must": ["items"],
        "check": lambda d: isinstance(d.get("items"), list) and len(d["items"]) > 0,
    },
    {
        "mock": "api-20",
        "method": "POST",
        "path": "/api/v1/notifications/n1/read",
        "why": "序号 20「全部已读 / 点消息」逐条标记已读（18-API 无批量接口；缺则 serve 对未定义 POST 兜底假成功）",
        "must": ["id"],
        "check": lambda d: bool(d.get("id")),
    },
    {
        "mock": "api-20",
        "method": "GET",
        "path": "/api/v1/reports/r1",
        "why": "序号 20 点「检测报告」消息的落地页 /pages/report/index?reportId=r1 取数（缺则落地页错误 toast 盖住落点证据）",
        "must": ["report_no", "total_score"],
        "check": lambda d: bool(d.get("report_no")) and d.get("total_score") is not None,
    },
    {
        "mock": "api-20",
        "method": "GET",
        "path": "/api/v1/provider/profile",
        "why": "序号 20 TabBar「工作台」落地页 /pages/workbench/index 取数",
        "must": ["id"],
        "check": lambda d: bool(d.get("id")),
    },
    {
        "mock": "api-20",
        "method": "GET",
        "path": "/api/v1/usage/summary",
        "why": "序号 20 TabBar「工作台」落地页 /pages/workbench/index 取数（用量/图例）",
        "must": ["total_tokens"],
        "check": lambda d: d.get("total_tokens") is not None,
    },
    # ---- 序号 21「【工作台与我的】我的 2」/pages/mine/index（7 个首屏 GET + 4 个落点页）----
    {
        "mock": "api-21",
        "method": "GET",
        "path": "/api/v1/provider/profile",
        "why": "序号 21 首屏：公司名 / 渠道商 / 已认证（缺则头部空态 + 错误 toast）",
        "must": ["company_name", "verified"],
        "check": lambda d: bool(d.get("company_name")) and d.get("verified") is True,
    },
    {
        "mock": "api-21",
        "method": "GET",
        "path": "/api/v1/payments",
        "why": "序号 21 钱包三金额（可提现余额 / 待结算 / 累计结算）",
        "must": ["available_balance", "pending_settlement", "total_settled"],
        "check": lambda d: d.get("available_balance") is not None and d.get("total_settled") is not None,
    },
    {
        "mock": "api-21",
        "method": "GET",
        "path": "/api/v1/quotes?page=1&pageSize=1",
        "why": "序号 21「我的报价单 3 个」计数（无汇总接口 → 取 total）",
        "must": ["total"],
        "check": lambda d: d.get("total") == 3,
    },
    {
        "mock": "api-21",
        "method": "GET",
        "path": "/api/v1/reports?page=1&pageSize=1",
        "why": "序号 21「检测报告 2 份」计数",
        "must": ["total"],
        "check": lambda d: d.get("total") == 2,
    },
    {
        "mock": "api-21",
        "method": "GET",
        "path": "/api/v1/contracts?page=1&pageSize=1&status=PENDING_SIGN",
        "why": "序号 21「我的合同 待签署 1」计数（10-PRD §4.2 状态机）",
        "must": ["total"],
        "check": lambda d: d.get("total") == 1,
    },
    {
        "mock": "api-21",
        "method": "GET",
        "path": "/api/v1/credentials?page=1&pageSize=1",
        "why": "序号 21「接入凭证 3 条」计数",
        "must": ["total"],
        "check": lambda d: d.get("total") == 3,
    },
    {
        "mock": "api-21",
        "method": "GET",
        "path": "/api/v1/notifications?page=1&pageSize=1&unread=true",
        "why": "序号 21「我的消息 待阅读 3」计数（未读口径）",
        "must": ["total"],
        "check": lambda d: d.get("total") == 3,
    },
    {
        "mock": "api-21",
        "method": "GET",
        "path": "/api/v1/usage/summary",
        "why": "序号 21「用量与对账」/「工作台」落地页取数（缺则落地页错误 toast 盖住落点证据）",
        "must": ["total_tokens"],
        "check": lambda d: d.get("total_tokens") is not None,
    },
    {
        "mock": "api-21",
        "method": "GET",
        "path": "/api/v1/auth/me",
        "why": "序号 21「账号与设置」落地页 /pages/settings/index 取数（authApi.me）",
        "must": ["phone"],
        "check": lambda d: bool(d.get("phone")),
    },
    # ---- 序号 22「【工作台与我的】我的与用量概览 2」/pages/usage/index（唯一读接口 /usage/summary，
    #      月份维度用查询串区分：首屏取当前月、picker 确认后取所选月）----
    {
        "mock": "api-22",
        "method": "GET",
        "path": "/api/v1/usage/summary?month=2026-09",
        "why": "序号 22 首屏取数：四宫格（请求数 / Token / 费用 / 较上月节省）",
        "must": ["month", "request_count", "total_tokens", "amount_total", "mom_saved_amount", "daily", "models", "cost"],
        "check": lambda d: d.get("month") == "2024-06" and d.get("request_count") == 1240000 and d.get("total_tokens") == 3860000000,
    },
    {
        "mock": "api-22",
        "method": "GET",
        "path": "/api/v1/usage/summary?month=2024-06",
        "why": "序号 22 月份 picker 确认后的第二次取数（本轮交互证据：serve 实收 ?month=2024-06）",
        "must": ["month"],
        "check": lambda d: d.get("month") == "2024-06",
    },
    {
        "mock": "api-22",
        "method": "GET",
        "path": "/api/v1/usage/summary",
        "why": "序号 22 趋势卡：7 个逐日点（stat_date + total_tokens → 折线 / 面积 / 横轴标签）",
        "must": ["daily"],
        "check": lambda d: len(d.get("daily") or []) == 7
        and all(x.get("stat_date") and x.get("total_tokens") for x in d["daily"]),
    },
    {
        "mock": "api-22",
        "method": "GET",
        "path": "/api/v1/usage/summary",
        "why": "序号 22 模型用量分布卡：4 行占比 42/31/21/6（share → 条宽 / 百分比）",
        "must": ["models"],
        "check": lambda d: [m.get("model_name") for m in (d.get("models") or [])]
        == ["gpt-4o-mini", "claude-3-5-sonnet", "gpt-4o", "其他"]
        and [m.get("share") for m in d["models"]] == [42, 31, 21, 6],
    },
    {
        "mock": "api-22",
        "method": "GET",
        "path": "/api/v1/usage/summary",
        "why": "序号 22 成本构成卡：输入/输出/平台服务费（费率 8）+ 合计",
        "must": ["cost"],
        "check": lambda d: d["cost"].get("input") == 4120
        and d["cost"].get("output") == 8240
        and d["cost"].get("platform_fee") == 500
        and d["cost"].get("platform_fee_rate") == 8
        and d["cost"].get("total") == 12860,
    },
    {
        "mock": "api-23",
        "method": "GET",
        "path": "/api/v1/auth/me",
        "why": "序号 23 账号信息卡三行数据源：手机号/微信绑定/短信通知开关",
        "must": ["phone", "wechat_bound", "sms_two_factor"],
        "check": lambda d: d.get("phone") == "13812346621"
        and d.get("wechat_bound") is True
        and d.get("sms_two_factor") is True
        and d.get("wechat_subscribed") is True,
    },
    {
        "mock": "api-23",
        "method": "POST",
        "path": "/api/v1/auth/logout",
        "why": "序号 23 退出登录：二次确认后 POST /auth/logout（body 无需字段）",
        "check": lambda d: True,
    },
]


KNOWN = {c["mock"] for c in CHECKS}


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def wait_ready(port, tries=40):
    for _ in range(tries):
        try:
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
            c.request("GET", "/index.html")
            c.getresponse().read()
            c.close()
            return True
        except Exception:
            time.sleep(0.25)
    return False


def request(port, method, path):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    body = b"" if method != "GET" else None
    c.request(method, path, body=body, headers={"Content-Type": "application/json"})
    r = c.getresponse()
    raw = r.read().decode("utf-8", "replace")
    c.close()
    return r.status, raw


def run_group(only, exact=False):
    mock = os.path.join(MOCK_ROOT, only or "api")
    port = free_port()
    srv = subprocess.Popen(
        [sys.executable, os.path.join(MOCK_ROOT, "serve.py"), PAGES, mock, str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    fails = []
    try:
        if not wait_ready(port):
            print("FAIL  serve.py 未就绪（port=%d）" % port)
            return 1
        # --mock 允许传变体目录名（如 api-tmp-noauth / api-tmp-d3-nomedia）：按前缀归到基础 mock 名，
        # 否则变体会一条检查都不跑。⚠️ 只对 `-tmp-` 变体生效：早年写成「只要以 base- 开头就算变体」，
        # 会让 api-15 这类「页面专属 mock 目录」误匹配到 api 的所有检查（2026-09-16 序号 15 轮修）。
        def _is_variant(base):
            return only is not None and only.startswith(base + "-tmp-")

        checks = [
            c
            for c in CHECKS
            if only is None or c["mock"] == only or (not exact and only not in KNOWN and _is_variant(c["mock"]))
        ]
        if only is not None and not checks:
            print("WARN  mock 目录 %s 没有任何 check（只跑反向体检）—— 若该页会调接口，请往 CHECKS 里补一条" % only)
        for c in checks:
            status, raw = request(port, c["method"], c["path"])
            if status != 200:
                fails.append((c["path"], "HTTP %d：%s" % (status, raw[:120])))
                print("FAIL  %-4s %-32s HTTP %d  ← %s" % (c["method"], c["path"], status, c["why"]))
                continue
            try:
                payload = json.loads(raw)
            except ValueError as exc:
                fails.append((c["path"], "响应不是 JSON：%s" % exc))
                print("FAIL  %-4s %-32s 响应非 JSON" % (c["method"], c["path"]))
                continue
            data = payload.get("data") if isinstance(payload, dict) else None
            missing = [k for k in c.get("must") or [] if not isinstance(data, dict) or k not in data]
            ok = not missing and (c["check"] is None or bool(c["check"](data or {})))
            if not ok:
                detail = "缺键 %s" % ",".join(missing) if missing else "载荷不满足断言"
                fails.append((c["path"], detail))
                print("FAIL  %-4s %-32s %s" % (c["method"], c["path"], detail))
            else:
                print("PASS  %-4s %-32s code=%s  ← %s" % (c["method"], c["path"], payload.get("code"), c["why"]))

        # 反向体检：mock 目录里已有的每个文件都能在自己对应的路径上取到（防映射/命名错位）
        orphan = []
        for dirpath, _dirs, files in os.walk(mock):
            for name in files:
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, mock).replace(os.sep, "/")
                method = "GET"
                if rel.endswith("/index"):
                    path = "/api/" + rel[: -len("/index")]
                elif "." in name:
                    path, method = "/api/" + rel.rsplit(".", 1)[0], name.rsplit(".", 1)[1].upper()
                else:
                    path, method = "/api/" + rel, name.upper() if name.islower() and name in (
                        "post", "put", "delete", "get") else "GET"
                if method not in ("GET", "POST", "PUT", "DELETE"):
                    continue
                status, _raw = request(port, method, path)
                if status != 200:
                    orphan.append((method, path, status))
        if orphan:
            for method, path, status in orphan:
                print("FAIL  反向体检 %-4s %-32s HTTP %d" % (method, path, status))
            fails.append(("反向体检", "%d 个 fixture 取不到" % len(orphan)))
        else:
            print("PASS  反向体检：mock 目录 %s 下所有 fixture 均可按路径取到" % (only or "api"))
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=5)
        except Exception:
            srv.kill()

    print("---")
    print("结论[%s]：%s（FAIL %d）" % (only or "api", "全部 PASS" if not fails else "存在 FAIL", len(fails)))
    return 1 if fails else 0


def main():
    only = None
    if "--mock" in sys.argv:
        only = sys.argv[sys.argv.index("--mock") + 1]
    # 不带 --mock 时：按每条 check 自带的 mock 目录名分组，各起一次 serve。
    # （否则 api-11 的路径会打到 api 目录上 → 永久假 FAIL，掩盖真实缺口）
    groups = [only] if only else sorted({c["mock"] for c in CHECKS})
    total = 0
    for g in groups:
        total += run_group(g, exact=True) if only is None else run_group(g)
    print("=== 汇总：%d 个 mock 目录 · FAIL 合计 %d ===" % (len(groups), total))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
