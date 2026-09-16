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
]


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


def main():
    only = None
    if "--mock" in sys.argv:
        only = sys.argv[sys.argv.index("--mock") + 1]
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
        # --mock 允许传变体目录名（如 api-tmp-noauth）：按前缀归到基础 mock 名，否则变体会一条检查都不跑
        checks = [
            c
            for c in CHECKS
            if only is None or c["mock"] == only or only.startswith(c["mock"] + "-")
        ]
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
    print("结论：%s（FAIL %d）" % ("全部 PASS" if not fails else "存在 FAIL", len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
