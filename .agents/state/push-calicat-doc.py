#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 docs/api/接口字段级schema.md 作为 PRD 卡推回 Calicat 文件（设计侧真源同步）。

用法：
    python .agents/state/push-calicat-doc.py [--dry-run]

注意：中文请求体不能经 bash 拼 JSON（会变 GBK）——本脚本用 Python 构造 JSON 再传 argv。
"""
import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(ROOT, "docs", "api", "接口字段级schema.md")
FILE_ID = "2095515676955668480"
CALICAT = os.path.expanduser("~/.calicat-cli/bin/calicat.exe")
TITLE = "18-补充·接口字段级schema"
MAX_CHARS = 18000

# Calicat 建卡接口对超大 body 会 524（实测 6.1k 字失败）→ 卡片只放摘要，完整版留在仓库
SUMMARY = """# 接口字段级 schema（供应商端补充）

**性质**：`18-API设计OpenAPI.md` 仅给路径 + 通用约定（完整 spec 在其 `05-架构/03-API设计-openapi.yaml`）。本卡为**供应商端在用接口的字段级补充**。
**完整版（含每字段单位/来源/错误码）**：仓库 `docs/api/接口字段级schema.md`。

**字段依据（不新造字段）**：`15-数据模型ER与数据字典.md`（`aap_usage_hourly`）· `11-同步与用量统计PRD.md`（小时用量表、对账视图指标）· `17-零歧义执行规格spec.md` §3 实体（Provider / ProviderAccount）· `18-API设计OpenAPI.md` 通用约定。

**决策（2026-09-16 用户拍板）**：JSON 字段一律 **snake_case**，与数据字典 1:1 同名，不做 camelCase 转换。

## 1. GET /usage/summary（工作台 / 用量页）
`provider_id, stat_from, stat_to, request_count, prompt_tokens, completion_tokens, total_tokens, cache_read_tokens, cache_write_tokens, cache_write_1h_tokens, image_input_tokens, audio_input_tokens, video_input_tokens(扩展), cache_hit_rate(0-1), cache_parse_rate(0-1), quota_raw, cost_usd, amount_total, mom_rate(0-1,可负), actual_unit_price(USD/1M), deviation_rate(0-1,>0.05 告警), tier_distribution{档位名:token}, models[]{model_name, request_count, total_tokens, amount}`

## 2. GET /usage/hourly（分时用量）
`data={list:[{stat_hour, channel_id, channel_name, model_name, group_name, request_count, prompt_tokens, completion_tokens, total_tokens, cache_read_tokens, cache_write_tokens, cache_write_1h_tokens, image_input_tokens, audio_input_tokens, quota_raw, cost_usd, cache_parse_status(OK|NO_CACHE_FIELD), source(LOG_API|LOG_DB)}], page, pageSize, total}`

## 3. GET /provider/profile（档案 / 档案编辑 / 工作台抬头）
`provider_id, provider_code(AAP-P-{6位}), short_name, company_name, uscc, contact{name, phone_masked, email}, qualification_files[]{file_id, file_name, size, uploaded_at, type}, status(ProviderStatus 12 态), recheck_interval_days, manual_override, override_reason(override=true 时必填 R-47a), account{phone_masked, role, wx_bound}, created_at, updated_at`
写：`PUT /provider/profile`（`Idempotency-Key` + `If-Match`；校验失败 `E-1001`）

## 4. 前端落地约定
百分比**一律由真实数值计算**（`percentOf`），不得沿用设计稿硬编码百分比 —— page-2-b 设计图例「音频 6% + 视频 6%」合计 106%，按此规则归一到真实占比；字段缺失显示占位符，不用 0 冒充（例外：`cache_parse_status=NO_CACHE_FIELD` 明确记 0，依据 11-PRD U2）。"""



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--summary", action="store_true", help="推送摘要版卡片（大 body 会 524）")
    a = ap.parse_args()

    if a.summary:
        content = SUMMARY
    else:
        with open(DOC, encoding="utf-8") as f:
            content = f.read()
        if len(content) > MAX_CHARS:
            content = content[:MAX_CHARS] + "\n\n> （超长截断，完整版见仓库 docs/api/接口字段级schema.md）"
    print(f"文档 {len(content)} 字符，标题《{TITLE}》，目标文件 {FILE_ID}")

    payload = json.dumps(
        {"file_id": FILE_ID, "document_title": TITLE, "document_content": content},
        ensure_ascii=False,
    )
    if a.dry_run:
        print(payload[:400], "...")
        return 0

    exe = CALICAT if os.path.exists(CALICAT) else "calicat"
    proc = subprocess.run(
        [exe, "tools-call", "--name", "create_document", "--args", payload],
        capture_output=True,
    )
    out = proc.stdout.decode("utf-8", errors="replace")
    err = proc.stderr.decode("utf-8", errors="replace")
    print("exit:", proc.returncode)
    print("stdout:", out[:2000])
    if err.strip():
        print("stderr:", err[:800])
    try:
        body = json.loads(out)
        text = body.get("content", [{}])[0].get("text", "")
        print("tool result:", text[:600])
    except Exception:  # noqa: BLE001
        pass
    return 0 if proc.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
