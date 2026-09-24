#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""业务闭环端到端验收（供应商端 → 管理端 → 上架 → 用量），真实 HTTP，非 mock。

为什么要单独有这个脚本
----------------------
`aap-client/tools/mp-e2e-full.mjs` 走的是**小程序编译产物**，验证的是「前端 api 层调用点
是否与后端契约一致」；它跑到「合同签署 / 用量查询」就结束了，**P8 是空的**：

    编译确认(ADM-CP04) → 上架同步(ADM-S07/S08/S09) → 用量归集(ADM-U02)

这一段此前**没有写入侧**（`aap_newapi_endpoint` / `aap_sync_task` / `aap_channel_binding`
全仓零 INSERT，见 `.agents/state/aap-decisions.md` D-SYNC-03），所以「进件流水线」只能到
「报价审核通过 + 合同签署」为止，走不到「渠道真的在 new-api 上架、用量真的回流」。
本脚本把这段接上，并且**只做直连 HTTP**（不依赖前端构建产物），用于逐环节对账。

它证明的是：**每一环节的库内状态机都真的走到了终点，而不是只有 HTTP 200。**

用法
----
    python tools/biz-closure-e2e.py \\
        --api-base http://127.0.0.1:8086/api/v1 \\
        --newapi-base http://127.0.0.1:9911 --newapi-key stub-local-key \\
        --provider-phone 13800138000 --admin-phone 13800000221

前置条件（缺一即会在对应步骤如实标红，不会静默跳过）：
1. 后端带 `AAP_ALLOW_LOOPBACK=true`（上架要向本地桩出站）、`AAP_SMS_EXPOSE_CODE=true`
   （联调取码）、`AAP_USAGE_LOG_FILE=<本脚本写的 mock 日志>`（用量归集源）启动；
2. 本地一体桩在跑：`python tools/newapi-stub.py --port 9911 --api-key stub-local-key`
   —— 它同时扮演「模型厂商」（预检/检测用 `/v1/models`）与「new-api 管理端」
   （上架用 `/api/channel/`、`/api/option/`）。

退出码：0 = 全部断言通过；1 = 有环节未闭环（报告里逐条给出）。
"""

from __future__ import annotations

import argparse
import io
import json
import re
import os
import random
import string
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

RESULTS: list[dict] = []


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class CallError(RuntimeError):
    def __init__(self, code, message, status=None):
        super().__init__("%s %s" % (code, message))
        self.code = code
        self.message = message
        self.status = status


class Client:
    """极简 HTTP 客户端：统一收敛业务码（code != 0 → CallError），便于按码断言。"""

    def __init__(self, api_base: str, token: str | None = None):
        self.api_base = api_base.rstrip("/")
        self.token = token
        self.calls: list[tuple[str, str, int, str]] = []

    def call(self, method: str, path: str, body=None, raw: bool = False, files=None):
        url = self.api_base + path
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        data = None
        if files is not None:
            boundary = "----bizclosure" + uuid.uuid4().hex
            buf = io.BytesIO()
            for name, value in files.get("fields", {}).items():
                buf.write(("--%s\r\n" % boundary).encode())
                buf.write(('Content-Disposition: form-data; name="%s"\r\n\r\n' % name).encode())
                buf.write(str(value).encode())
                buf.write(b"\r\n")
            filename, content = files["file"]
            buf.write(("--%s\r\n" % boundary).encode())
            buf.write(('Content-Disposition: form-data; name="file"; filename="%s"\r\n' % filename).encode())
            buf.write(b"Content-Type: application/octet-stream\r\n\r\n")
            buf.write(content)
            buf.write(b"\r\n")
            buf.write(("--%s--\r\n" % boundary).encode())
            data = buf.getvalue()
            headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
        elif body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                status = resp.status
                text = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            status = exc.code
            text = exc.read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001
            self.calls.append((method, path, 0, "transport"))
            raise CallError("TRANSPORT", "%s %s: %s" % (method, path, exc))
        payload = None
        try:
            payload = json.loads(text)
        except Exception:  # noqa: BLE001
            payload = {"_raw": text[:400]}
        code = str(payload.get("code", "?")) if isinstance(payload, dict) else "?"
        self.calls.append((method, path, status, code))
        if raw:
            return status, payload
        if status >= 400 or code != "0":
            raise CallError(code, (payload or {}).get("message", "HTTP %s" % status), status)
        return payload.get("data")


# ---- 凭据脱敏出口（引入于收尾轮 R358；历史：登录响应体原样进证据 → 真实 access/refresh token 被写进 git）----
SECRET_KEY_PAT = ('token|access_?token|refresh_?token|id_?token|api_?key|apikey|secret'
                  '|client_?secret|password|passwd|authorization|credentials?')
JWT_VALUE_RE = re.compile('eyJ[A-Za-z0-9_-]{8,}[.][A-Za-z0-9_-]{8,}[.][A-Za-z0-9_-]{8,}')
KV_SECRET_RE = re.compile('((?:["\'])(?:' + SECRET_KEY_PAT + ')(?:["\'])[ ]*:[ ]*(?:["\']))([^"\']{12,})(["\'])', re.I)


def mask_secrets(text: str) -> str:
    """把凭据值（JWT 形态 / 凭据类键名下的长值）替换为 <redacted len=N>。
    报告落盘与 stdout 都必须走这一出口 —— 它是「证据里不得有真实令牌」的唯一执行点。"""
    text = KV_SECRET_RE.sub(
                lambda m: m.group(1) + '<redacted len=%d>' % len(m.group(2)) + m.group(3), text)
    return JWT_VALUE_RE.sub(lambda m: '<redacted len=%d>' % len(m.group(0)), text)


def step(phase: str, name: str, fn):
    started = time.time()
    try:
        detail = fn()
        RESULTS.append({"phase": phase, "name": name, "ok": True,
                        "detail": "" if detail is None else mask_secrets(str(detail)),
                        "ms": int((time.time() - started) * 1000)})
        print("  [OK]   [%s] %s%s" % (phase, name, (" — " + mask_secrets(str(detail))) if detail else ""), flush=True)
        return True, detail
    except CallError as exc:
        RESULTS.append({"phase": phase, "name": name, "ok": False,
                        "detail": "%s %s" % (exc.code, exc.message),
                        "ms": int((time.time() - started) * 1000)})
        print("  [FAIL] [%s] %s — %s %s" % (phase, name, exc.code, exc.message), flush=True)
        return False, exc
    except Exception as exc:  # noqa: BLE001
        RESULTS.append({"phase": phase, "name": name, "ok": False,
                        "detail": "%s: %s" % (type(exc).__name__, exc),
                        "ms": int((time.time() - started) * 1000)})
        print("  [FAIL] [%s] %s — %s: %s" % (phase, name, type(exc).__name__, exc), flush=True)
        return False, exc


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def dev_login(client: Client, phone: str, admin: bool):
    """短信登录（联调环境后端暴露 dev_code）。"""

    def send():
        return client.call("POST", "/auth/sms/send", {"phone": phone, "captcha": "".join(
            random.choices(string.ascii_uppercase + string.digits, k=4))})

    code = None
    try:
        send_result = send()
        code = (send_result or {}).get("dev_code") or (send_result or {}).get("code")
    except CallError as exc:
        if exc.code == "E-1903":   # 60s 频控：联调环境如实等待
            time.sleep(62)
            send_result = send()
            code = (send_result or {}).get("dev_code") or (send_result or {}).get("code")
        else:
            raise
    if not code:
        raise CallError("E2E-1", "未取到 dev_code（后端需 AAP_SMS_EXPOSE_CODE=true）")
    path = "/admin/auth/sms/login" if admin else "/auth/sms/login"
    data = client.call("POST", path, {"phone": phone, "smsCode": code})
    if not (data or {}).get("token"):
        raise CallError("E2E-2", "登录响应无 token")
    client.token = data["token"]
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="http://127.0.0.1:8086/api/v1")
    parser.add_argument("--newapi-base", default="http://127.0.0.1:9911")
    parser.add_argument("--newapi-key", default="stub-local-key")
    parser.add_argument("--provider-phone", default="13800138000")
    parser.add_argument("--admin-phone", default="13800000221")
    parser.add_argument("--usage-log", default="")
    parser.add_argument("--report", default="")
    args = parser.parse_args()

    usage_log = args.usage_log or ("%s/biz-closure-usage-log.json" % (
        __import__("os").environ.get("LOCALAPPDATA", "/tmp").replace("\\", "/") + "/Temp"))
    report_path = args.report or (".agents/state/evidence/biz-closure-%s.json"
                                  % datetime.now().strftime("%Y%m%d-%H%M%S"))

    provider = Client(args.api_base)
    admin = Client(args.api_base)
    state: dict = {}
    print("业务闭环验收（真实 HTTP）→ %s" % args.api_base, flush=True)

    # ── P0 认证 ───────────────────────────────────────────────────────────────
    print("\nP0 · 认证", flush=True)
    ok, info = step("P0", "供应商短信登录（AUTH-01/02）", lambda: dev_login(provider, args.provider_phone, False))
    if ok:
        state["provider_id"] = info.get("providerId") or info.get("provider_id")
    ok, info = step("P0", "管理端短信登录（ADM-AUTH01）", lambda: dev_login(admin, args.admin_phone, True))
    if ok:
        state["admin_role"] = info.get("role")
    if not state.get("provider_id"):
        step("P0", "取供应商 ID（PROV-01）", lambda: state.update(
            provider_id=(provider.call("GET", "/provider/profile") or {}).get("id")))
    assert_true(state.get("provider_id"), "未取到 provider_id，后续环节无法归属供应商")

    # ── P1 档案 ───────────────────────────────────────────────────────────────
    print("\nP1 · 供应商档案", flush=True)

    def save_profile():
        uniq = "".join(random.choices(string.ascii_uppercase + string.digits, k=9))
        return provider.call("PUT", "/provider/profile", {
            "short_name": "闭环供应商",
            "company_name": "闭环验收科技有限公司",
            "uscc": ("91110108MA" + uniq)[:18],
            "industry_category": "ORIGINAL",
            "province": "广东省", "city": "深圳市",
            "contact_name": "闭环联系人",
            "contact_phone": args.provider_phone,
            "company_intro": "业务闭环验收脚本写入",
        }) or {}

    step("P1", "PUT /provider/profile（唯一 USCC，脚本可重跑）", save_profile)

    # ── P2 凭证 ───────────────────────────────────────────────────────────────
    print("\nP2 · 测试凭证（指向一体桩的厂商角色）", flush=True)

    def create_credential():
        try:
            data = provider.call("POST", "/credentials", {
                "alias": "闭环凭证-%s" % datetime.now().strftime("%m%d%H%M%S"),
                "base_url": args.newapi_base + "/v1",
                "api_key": "sk-bizclosure-" + uuid.uuid4().hex[:12],
                "primary_flag": True,
                "declared_vendor": "StubVendor",
                "declared_rpm": 600,
                "declared_context_window": 128000,
                "model_list": [{"model_name": "gpt-4o"}, {"model_name": "gpt-4o-mini"}],
            }) or {}
        except CallError as exc:
            if exc.code != "E-1104":   # 指纹重复 → 复用既有凭证，保证可重跑
                raise
            items = _items(provider.call("GET", "/credentials?page=1&pageSize=50"))
            found = [x for x in items if str(x.get("alias", "")).startswith("闭环凭证")]
            if not found:
                raise
            data = found[0]
        cred_id = data.get("id") or data.get("credential_id")
        assert_true(cred_id, "凭证响应无 id")
        state["credential_id"] = str(cred_id)
        return "credential_id=%s" % cred_id

    step("P2", "POST /credentials（上游=%s/v1）" % args.newapi_base, create_credential)

    # ── P3 检测（预检建任务 → 真跑探测 → 必要时人工放行）────────────────────
    print("\nP3 · 检测引擎", flush=True)

    def precheck():
        if not state.get("credential_id"):
            raise CallError("E2E-3", "P2 未拿到 credential_id")
        data = provider.call("POST", "/credentials/%s/precheck" % state["credential_id"]) or {}
        job_id = data.get("job_id") or data.get("jobId") or data.get("detection_job_id")
        assert_true(job_id, "预检响应无 job_id")
        state["job_id"] = str(job_id)
        return "job_id=%s status=%s" % (job_id, data.get("status"))

    step("P3", "POST /credentials/{id}/precheck（CRED-05）", precheck)

    def wait_terminal():
        if not state.get("job_id"):
            raise CallError("E2E-4", "无 job_id")
        deadline = time.time() + 150
        last = None
        while time.time() < deadline:
            job = provider.call("GET", "/detection-jobs/%s" % state["job_id"]) or {}
            last = job.get("status")
            if last in ("COMPLETED", "SUCCEEDED", "PASSED", "FAILED", "DETECT_FAILED", "CANCELED", "MANUAL"):
                return "job 终态=%s（%d 次轮询）" % (last, 1)
            time.sleep(5)
        raise CallError("E2E-5", "检测任务 150s 未到终态，最后状态=%s" % last)

    ok, _ = step("P3", "轮询 /detection-jobs/{jobId} 至终态（DET-02）", wait_terminal)

    def release_if_needed():
        cred = provider.call("GET", "/credentials/%s" % state["credential_id"]) or {}
        status = cred.get("detection_status")
        state["detection_status"] = status
        if status == "PASS":
            return "检测已 PASS，无需人工放行"
        admin.call("POST", "/detection-jobs/%s/release" % state["job_id"],
                   {"override_reason": "闭环验收：本地桩无真实探测语义，按 DET-06 人工放行"})
        cred = provider.call("GET", "/credentials/%s" % state["credential_id"]) or {}
        state["detection_status"] = cred.get("detection_status")
        assert_true(state["detection_status"] == "PASS",
                    "人工放行后 detection_status 仍为 %s" % state["detection_status"])
        return "DET-06 人工放行后 detection_status=PASS"

    step("P3", "检测状态归位（PASS，否则 DET-06 放行）", release_if_needed)

    # ── P4 报价 ───────────────────────────────────────────────────────────────
    print("\nP4 · 报价单与定价", flush=True)

    def create_quote():
        data = provider.call("POST", "/quotes", {
            "name": "闭环报价单-%s" % datetime.now().strftime("%m%d-%H%M%S"),
            "credential_id": state["credential_id"],
            "currency": "USD",
        }) or {}
        quote_id = data.get("id") or data.get("quote_id")
        assert_true(quote_id, "报价响应无 id")
        state["quote_id"] = str(quote_id)
        provider.call("POST", "/quotes/%s/items" % quote_id, {"items": [{"model_name": "gpt-4o"}]})
        return "quote_id=%s" % quote_id

    step("P4", "POST /quotes + 明细（QT-02/QT-05）", create_quote)

    def price_item():
        items = _items(provider.call("GET", "/quotes/%s/items" % state["quote_id"]))
        assert_true(items, "报价明细为空")
        item_id = items[0].get("id") or items[0].get("item_id")
        state["item_id"] = str(item_id)
        provider.call("PUT", "/quotes/items/%s" % item_id, {
            "model_alias": "gpt-4o", "input_price": 2.5, "output_price": 10,
            "cache_read_price": 1.25, "cache_write_price": 2.5,
        })
        return "item_id=%s 已定价" % item_id

    step("P4", "PUT /quotes/items/{id} 定价（QT-08）", price_item)
    step("P4", "POST /quotes/{id}/submit（QT-09）",
         lambda: (provider.call("POST", "/quotes/%s/submit" % state["quote_id"]) or {}).get("status", "已提交"))

    # ── P5 审核 → 合同 ────────────────────────────────────────────────────────
    print("\nP5 · 管理端审核 → 合同签署闭环", flush=True)

    def approve_review():
        items = _items(admin.call("GET", "/admin/reviews"))
        mine = [x for x in items if str(x.get("quote_id") or x.get("quoteId")) == state["quote_id"]]
        target = (mine or items)[0] if (mine or items) else None
        assert_true(target, "无待审记录")
        review_id = target.get("id") or target.get("review_id")
        admin.call("POST", "/admin/reviews/%s/claim" % review_id, {})
        admin.call("POST", "/admin/reviews/%s/approve" % review_id, {"comment": "闭环验收自动通过"})
        return "review_id=%s 已审核通过" % review_id

    step("P5", "[ADMIN] 领取并审核通过（ADM-R02/R03）", approve_review)

    def issue_contract():
        items = _items(admin.call("GET", "/admin/contracts"))
        mine = [x for x in items if str(x.get("quote_id") or x.get("quoteId")) == state["quote_id"]]
        contract = (mine or items)[0] if (mine or items) else None
        assert_true(contract, "审核通过后未生成合同")
        contract_id = contract.get("id") or contract.get("contract_id")
        upload = admin.call("POST", "/files", files={
            "fields": {"biz_type": "CONTRACT"},
            "file": ("biz-closure-contract.txt",
                     ("闭环验收合同占位文件 %s" % now_iso()).encode("utf-8")),
        }) or {}
        file_id = upload.get("file_id") or upload.get("id")
        assert_true(file_id, "文件服务未返回 file_id")
        admin.call("POST", "/admin/contracts/%s/issue" % contract_id, {"file_id": file_id})
        state["contract_id"] = str(contract_id)
        return "contract_id=%s 已签发（file_id=%s）" % (contract_id, file_id)

    step("P5", "[ADMIN] 合同签发（ADM-CT02，带真实文件）", issue_contract)

    def sign_contract():
        provider.call("POST", "/contracts/%s/sign" % state["contract_id"], {"sign_method": "SEAL"})
        detail = provider.call("GET", "/contracts/%s" % state["contract_id"]) or {}
        return "供应商签署完成 status=%s" % detail.get("status")

    step("P5", "POST /contracts/{id}/sign（CON-04，SEAL）", sign_contract)

    def confirm_sign():
        data = admin.call("POST", "/admin/contracts/%s/confirm-sign" % state["contract_id"]) or {}
        assert_true(str(data.get("status")) in ("ACTIVE", "EFFECTIVE", "SIGNED"),
                    "确认签署后合同状态异常：%s" % data.get("status"))
        return "合同生效 status=%s" % data.get("status")

    step("P5", "[ADMIN] 确认签署（ADM-CT03）→ 合同生效", confirm_sign)

    # ── P6 打款 ───────────────────────────────────────────────────────────────
    print("\nP6 · 打款留痕", flush=True)

    def record_payment():
        upload = admin.call("POST", "/files", files={
            "fields": {"biz_type": "PAYMENT_VOUCHER"},
            "file": ("biz-closure-voucher.txt", ("打款凭证 %s" % now_iso()).encode("utf-8")),
        }) or {}
        voucher_id = upload.get("file_id") or upload.get("id")
        assert_true(voucher_id, "文件服务未返回 file_id")
        data = admin.call("POST", "/admin/payments", {
            "contract_id": state["contract_id"],
            "amount": 1234.56, "currency": "USD", "voucher_file_id": voucher_id,
            "paid_at": now_iso(), "remark": "闭环验收自动记录",
        }) or {}
        payment_id = data.get("id") or data.get("payment_id")
        assert_true(payment_id, "打款响应无 id")
        state["payment_id"] = str(payment_id)
        return "payment_id=%s status=%s" % (payment_id, data.get("status"))

    step("P6", "[ADMIN] 记录打款（ADM-PAY04，带凭证文件）", record_payment)

    def confirm_payment():
        data = admin.call("POST", "/admin/payments/%s/confirm" % state["payment_id"]) or {}
        assert_true(str(data.get("status")) == "CONFIRMED",
                    "确认打款后状态异常：%s" % data.get("status"))
        return "打款已确认 CONFIRMED"

    step("P6", "[ADMIN] 确认打款（ADM-PAY02）", confirm_payment)

    # ── P7 编译（闸门③）──────────────────────────────────────────────────────
    print("\nP7 · 编译与人工确认（闸门③）", flush=True)

    def compile_quote():
        data = admin.call("POST", "/admin/quotes/%s/compile" % state["quote_id"]) or {}
        comp_id = data.get("compilation_id") or data.get("id")
        assert_true(comp_id, "编译响应无 compilation_id")
        state["compilation_id"] = str(comp_id)
        return "compilation_id=%s gate_status=%s" % (comp_id, data.get("gate_status"))

    step("P7", "[ADMIN] POST /admin/quotes/{id}/compile（ADM-Q01）", compile_quote)

    def verify_compilation():
        report = admin.call("POST", "/admin/compilations/%s/verify" % state["compilation_id"]) or {}
        assert_true(report.get("status") == "PASSED",
                    "模拟验证未通过：status=%s failed_field=%s" % (report.get("status"), report.get("failed_field")))
        return "验证通过 %s/%s 用例" % (report.get("case_passed"), report.get("case_total"))

    step("P7", "[ADMIN] 模拟验证（ADM-CP03）", verify_compilation)

    def confirm_compilation():
        data = admin.call("POST", "/admin/compilations/%s/confirm" % state["compilation_id"]) or {}
        assert_true(data.get("gate_status") == "CONFIRMED", "确认后 gate_status=%s" % data.get("gate_status"))
        assert_true(data.get("publish_blocked") is False, "确认后 publish_blocked=%s" % data.get("publish_blocked"))
        return "gate_status=CONFIRMED publish_blocked=false"

    step("P7", "[ADMIN] 人工确认（ADM-CP04）", confirm_compilation)

    # ── P8 上架同步（本次新增的写入侧）──────────────────────────────────────
    print("\nP8 · 上架同步（ADM-S07/S08/S09，闭环最后一段）", flush=True)

    def register_endpoint():
        data = admin.call("POST", "/admin/newapi-endpoints", {
            "name": "闭环验收 new-api 端点-%s" % datetime.now().strftime("%m%d%H%M%S"),
            "base_url": args.newapi_base,
            "api_key": args.newapi_key,
            "readonly": False,
        }) or {}
        endpoint_id = data.get("id")
        assert_true(endpoint_id, "登记端点响应无 id")
        assert_true(data.get("api_key_mask"), "响应未回掩码（api_key_mask 为空）")
        assert_true(args.newapi_key not in json.dumps(data), "响应泄露了明文 api_key")
        state["endpoint_id"] = str(endpoint_id)
        return "endpoint_id=%s api_key_mask=%s（无明文）" % (endpoint_id, data.get("api_key_mask"))

    step("P8", "[ADMIN] 登记 new-api 端点（ADM-S07）", register_endpoint)

    def create_sync_task():
        data = admin.call("POST", "/admin/sync/tasks", {
            "provider_id": str(state["provider_id"]),
            "compilation_id": str(state["compilation_id"]),
        }) or {}
        task_id = data.get("id") or data.get("task_id")
        assert_true(task_id, "同步任务响应无 id")
        assert_true(data.get("task_no"), "同步任务缺少 task_no")
        state["sync_task_id"] = str(task_id)
        return "task_id=%s task_no=%s status=%s" % (task_id, data.get("task_no"), data.get("status"))

    step("P8", "[ADMIN] 发起上架同步（ADM-S08）", create_sync_task)

    def execute_sync():
        data = admin.call("POST", "/admin/sync/tasks/%s/execute" % state["sync_task_id"], {}) or {}
        state["sync_status"] = data.get("status")
        assert_true(data.get("status") == "SYNCED", "执行后任务状态=%s（期望 SYNCED）" % data.get("status"))
        assert_true(data.get("readback_equal") is True, "回读比对未通过：readback_equal=%s" % data.get("readback_equal"))
        return "任务 SYNCED，回读一致"

    step("P8", "[ADMIN] 执行上架（ADM-S09，读前写后三段式）", execute_sync)

    def assert_binding_and_provider():
        bindings = _items(admin.call("GET", "/admin/channel-bindings"))
        mine = [x for x in bindings if str(x.get("provider_id")) == str(state["provider_id"])]
        assert_true(mine, "未发现该供应商的渠道绑定（%d 条总记录）" % len(bindings))
        binding = mine[0]
        assert_true(str(binding.get("status")) == "ENABLED", "渠道绑定状态=%s（期望 ENABLED）" % binding.get("status"))
        state["channel_id"] = binding.get("channel_id")
        providers = _items(admin.call("GET", "/admin/providers"))
        target = [x for x in providers if str(x.get("id")) == str(state["provider_id"])]
        provider_status = target[0].get("status") if target else None
        assert_true(str(provider_status) == "PUBLISHED",
                    "供应商状态=%s（期望 PUBLISHED）" % provider_status)
        return "binding=%s channel_id=%s ENABLED；provider=PUBLISHED" % (binding.get("id"), binding.get("channel_id"))

    step("P8", "库内终态核对（ADM-S04 + ADM-P01）", assert_binding_and_provider)

    # ── P9 用量归集（mock 日志源）─────────────────────────────────────────────
    print("\nP9 · 用量归集与对账视图", flush=True)

    def write_usage_log():
        channel_id = int(state["channel_id"])
        stat_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        payload = {"source": "biz-closure-e2e", "buckets": [{
            "stat_hour": stat_hour.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "channel_id": channel_id, "channel_name": "闭环验收渠道",
            "provider_id": int(state["provider_id"]),
            "model_name": "gpt-4o", "group_name": "default",
            "request_count": 120, "prompt_tokens": 12000, "completion_tokens": 6000, "total_tokens": 18000,
            "cache_read_tokens": 2000, "cache_write_tokens": 1000, "cache_write_1h_tokens": 500,
            "image_input_tokens": 0, "audio_input_tokens": 0, "video_input_tokens": 0,
            "quota_raw": 12345.6, "cost_usd": 12.34,
            "cache_parse_status": "OK", "source": "LOG_API",
            "collected_at": now_iso(),
        }]}
        with open(usage_log, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        state["window_from"] = stat_hour.strftime("%Y-%m-%dT%H:%M:%SZ")
        state["window_to"] = (stat_hour + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        return "mock 日志已写 %s（stat_hour=%s）" % (usage_log, payload["buckets"][0]["stat_hour"])

    step("P9", "写 mock 用量日志源", write_usage_log)

    def refresh_usage():
        data = admin.call("POST", "/admin/usage/refresh",
                          {"from": state["window_from"], "to": state["window_to"]}) or {}
        # 响应字段真名是 `batch_total`（ADM-U02 契约）——按响应实测口径断言，不套用猜测的字段名
        assert_true(int(data.get("batch_total") or 0) >= 1, "刷新未读到任何桶：%s" % data)
        # upsert 语义：同一 (stat_hour, channel_id, model) 桶重复刷新走 updated（幂等命中），
        # 故判据是 inserted + updated ≥ 1，而不是「每次都必须有新插入」。
        changed = int(data.get("inserted") or 0) + int(data.get("updated") or 0)
        assert_true(changed >= 1, "刷新未产生任何写入（inserted+updated=0）：%s" % data)
        return "batch_total=%s inserted=%s batch_id=%s" % (data.get("batch_total"), data.get("inserted"), data.get("batch_id"))

    step("P9", "[ADMIN] POST /admin/usage/refresh（ADM-U02）", refresh_usage)

    def provider_usage():
        summary = provider.call("GET", "/usage/summary?from=%s&to=%s" % (state["window_from"], state["window_to"])) or {}
        total = summary.get("total_tokens") or summary.get("total", {}).get("tokens")
        assert_true(int(total or 0) > 0, "供应商侧用量汇总为 0：%s" % summary)
        return "供应商可见 total_tokens=%s" % total

    step("P9", "供应商端读用量（USE-01）", provider_usage)

    def admin_usage():
        page = admin.call("GET", "/admin/usage/hourly?from=%s&to=%s" % (state["window_from"], state["window_to"])) or {}
        items = _items(page)
        mine = [x for x in items if str(x.get("provider_id")) == str(state["provider_id"])]
        assert_true(mine, "管理端用量视图未包含该供应商（%d 条）" % len(items))
        return "管理端可见 %d 条该供应商桶" % len(mine)

    step("P9", "[ADMIN] 管理端读用量（ADM-U01）", admin_usage)

    # ── 汇总 ─────────────────────────────────────────────────────────────────
    passed = sum(1 for r in RESULTS if r["ok"])
    failed = [r for r in RESULTS if not r["ok"]]
    report = {
        "generated_at": now_iso(), "api_base": args.api_base,
        "provider_id": state.get("provider_id"), "quote_id": state.get("quote_id"),
        "compilation_id": state.get("compilation_id"), "sync_task_id": state.get("sync_task_id"),
        "channel_id": state.get("channel_id"),
        "steps_total": len(RESULTS), "steps_passed": passed, "steps_failed": len(failed),
        "results": RESULTS,
    }
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print("\n汇总：%d/%d 步通过；报告 %s" % (passed, len(RESULTS), report_path), flush=True)
    if failed:
        print("未闭环环节：", flush=True)
        for row in failed:
            print("  - [%s] %s → %s" % (row["phase"], row["name"], row["detail"]), flush=True)
    return 0 if not failed else 1


def _items(page):
    if page is None:
        return []
    if isinstance(page, list):
        return page
    return page.get("items") or page.get("records") or []


if __name__ == "__main__":
    sys.exit(main())
