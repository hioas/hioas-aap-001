#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成 AAP 服务端接口模型：JSON Schema（2020-12）+ OpenAPI 3.1。

单一事实源 = 本脚本内的 MODELS / REQUESTS / PATHS 三张表。
产物：
  docs/backend/json-schema/common/*.schema.json
  docs/backend/json-schema/models/*.schema.json
  docs/backend/json-schema/requests/*.schema.json
  docs/backend/openapi.yaml

用法： python tools/gen-backend-models.py            # 生成
       python tools/gen-backend-models.py --check     # 只校验（生成到内存比对文件）
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs", "backend")
SCHEMA_DIR = os.path.join(DOCS, "json-schema")

ID = {"type": ["string", "null"], "description": "雪花 ID（对外 string，避免 JS 精度丢失；可空）"}
TS = {"type": ["string", "null"], "format": "date-time", "description": "RFC3339 UTC"}
STR = {"type": ["string", "null"]}
INT = {"type": ["integer", "null"]}
NUM = {"type": ["number", "null"]}
BOOL = {"type": ["boolean", "null"]}
DEC6 = {"type": ["number", "null"], "description": "numeric(18,6)：USD 或 USD/1M tokens"}
TOKENS = {"type": ["integer", "null"], "description": "词元计数（bigint）"}

ENUMS = {
    "ProviderStatus": ["PENDING_CREDENTIAL", "DETECTING", "DETECT_FAILED", "DETECT_PASSED", "QUOTING",
                       "QUOTE_SUBMITTED", "CONTRACT_PENDING", "SIGNED", "PAID", "PUBLISHED",
                       "SUSPENDED", "TERMINATED"],
    "DetectionJobStatus": ["QUEUED", "RUNNING", "PARTIAL_DONE", "COMPLETED", "REPORT_GENERATED", "FAILED"],
    "ProbeStatus": ["SUCCESS", "FAILED", "SKIPPED", "NOT_MEASURABLE"],
    "CredentialStatus": ["PENDING_PRECHECK", "PRECHECK_PASSED", "PRECHECK_FAILED", "ACTIVE", "INVALID"],
    "CredentialDetectionStatus": ["PENDING", "RUNNING", "PASS", "FAIL"],
    "QuoteStatus": ["DRAFT", "SUBMITTED", "IN_REVIEW", "REJECTED", "APPROVED", "CONTRACT_CREATED",
                    "CONVERTED", "VOID"],
    "ContractStatus": ["CREATED", "PENDING_SIGN", "SUPPLIER_SIGNED", "SIGNED", "ARCHIVED", "VOIDED"],
    "PaymentStatus": ["UNSETTLED", "PAYMENT_RECORDED", "CONFIRMED", "VOID"],
    "SyncStatus": ["NOT_SYNCED", "PENDING", "SYNCING", "SYNCED", "PARTIAL", "FAILED", "ENABLED",
                   "DISABLED", "ROLLED_BACK"],
    "TriggerType": ["FIRST", "MANUAL", "SCHEDULED"],
    "Role": ["SUPPLIER", "PROVIDER", "BIZ_OPERATOR", "TECH_OPS", "SUPER_ADMIN"],
    "ReportResult": ["PASS", "FAIL", "MANUAL_REVIEW"],
    "Confidence": ["HIGH", "MEDIUM", "LOW"],
    "TierField": ["len"],
    "PriceStrategy": ["OVERRIDE", "MULTIPLY"],
    "WeekdayScope": ["ALL", "WEEKDAY", "WEEKEND"],
    "CacheParseStatus": ["OK", "NO_CACHE_FIELD"],
    "IndustryCategory": ["ORIGINAL", "RESELLER", "AGGREGATOR"],
    "QuoteRejectReason": ["PRICE_TOO_HIGH", "PRICE_STRUCTURE_INVALID", "CACHE_PRICE_MISSING", "TECH_RISK",
                          "VALIDITY_ISSUE", "MISSING_INFO", "OTHER"],
    "AuditAction": ["CREDENTIAL_REVEAL", "QUOTE_CREATE", "QUOTE_SAVE", "QUOTE_SUBMIT", "QUOTE_WITHDRAW", "QUOTE_VOID", "QUOTE_APPROVE", "QUOTE_REJECT", "SYNC_WRITE_PRICE", "PROVIDER_SUSPEND", "PROVIDER_RESUME",
                    "CONTRACT_SIGN", "PAYMENT_CONFIRM", "DETECTION_RELEASE", "PROFILE_UPDATE", "AUTH_LOGIN",
                    "CONFIG_PUBLISH", "SYNC_EXECUTE"],
    "ResultCode": ["0", "E-1001", "E-1101", "E-1102", "E-1104", "E-1201", "E-1301", "E-1302", "E-1303",
                   "E-1304", "E-1305", "E-1401", "E-1402", "E-1403", "E-1404", "E-1405", "E-1406",
                   "E-1407", "E-1501", "E-1505", "E-1601", "E-1602", "E-1701", "E-1801", "E-1901",
                   "E-1902", "E-1903", "E-2001"],
}

# ---------------------------------------------------------------- models
MODELS: dict[str, dict] = {
    "page-meta": dict(required=["page", "pageSize", "total"], properties={
        "page": {"type": "integer", "minimum": 1},
        "pageSize": {"type": "integer", "minimum": 1, "maximum": 200},
        "total": {"type": "integer", "minimum": 0},
    }),
    "model-entry": dict(properties={
        "model_name": STR, "model_id": STR, "context_window": INT, "rpm": INT,
        "declared_tpm": INT, "vendor": STR,
    }),
    "vendor-group": dict(properties={
        "vendor": STR, "models": {"type": ["array", "null"], "items": {"$ref": "model-entry.schema.json"}},
    }),
    "file-asset": dict(required=["file_id"], properties={
        "file_id": ID, "file_name": STR, "size": INT, "size_bytes": INT, "content_type": STR,
        "type": STR, "uploaded_at": TS, "url": STR, "sha256": STR,
    }),
    "provider-qualification": dict(properties={
        "id": ID, "qualification_id": ID, "category": STR, "file_id": ID, "file_name": STR,
        "file_size": INT, "content_type": STR, "status": STR, "uploaded_at": TS,
    }),
    "provider-profile": dict(required=["provider_id", "status"], properties={
        "provider_id": ID, "id": ID, "provider_no": STR, "provider_code": STR,
        "providerCode": STR, "etag": STR,
        "short_name": STR, "short_code": STR,
        "company_name": STR, "companyName": STR, "uscc": STR, "unified_social_credit_code": STR,
        "industry_category": STR, "province": STR, "city": STR, "address": STR, "website": STR,
        "contact": {"type": ["object", "null"], "properties": {
            "name": STR, "phone_masked": STR, "email": STR, "title": STR}},
        "contact_name": STR, "contact_phone": STR, "contact_phone_masked": STR, "contact_title": STR,
        "contact_email": STR, "company_intro": STR, "completeness": INT,
        "qualification_files": {"type": ["array", "null"], "items": {"$ref": "file-asset.schema.json"}},
        "status": {"type": "string", "enum": ENUMS["ProviderStatus"]},
        "recheck_interval_days": INT, "manual_override": BOOL, "override_reason": STR,
        "account": {"type": ["object", "null"], "properties": {
            "phone_masked": STR, "role": STR, "wx_bound": BOOL}},
        "created_at": TS, "updated_at": TS, "version": INT,
    }),
    "credential-detail": dict(required=["id"], properties={
        "id": ID, "provider_id": ID, "alias": STR, "base_url": STR,
        "api_key_mask": STR, "api_key_masked": STR, "primary_flag": BOOL, "is_primary": BOOL,
        "declared_vendor": STR, "declared_rpm": INT, "declared_tpm": INT, "declared_context_window": INT,
        "model_list": {"type": ["array", "null"], "items": {"$ref": "model-entry.schema.json"}},
        "model_catalog": {"type": ["array", "null"], "items": {"$ref": "vendor-group.schema.json"}},
        "env_tag": STR, "status": {"type": ["string", "null"], "enum": ENUMS["CredentialStatus"] + [None]},
        "detection_status": {"type": ["string", "null"], "enum": ENUMS["CredentialDetectionStatus"] + [None]},
        "latest_report_id": ID, "precheck_passed": BOOL, "precheck_at": TS, "created_at": TS,
        "updated_at": TS, "version": INT,
    }),
    "credential-row": dict(required=["id"], properties={
        "id": ID, "alias": STR, "model_list": {"type": ["array", "null"], "items": {"type": "object"}},
        "created_at": TS, "detection_status": {"type": ["string", "null"],
                                               "enum": ENUMS["CredentialDetectionStatus"] + [None]},
        "latest_report_id": ID, "status": STR, "base_url": STR, "api_key_mask": STR,
    }),
    "credential-precheck": dict(properties={
        "id": ID, "credential_id": ID, "status": STR, "connectivity_ok": BOOL, "auth_ok": BOOL,
        "models_ok": BOOL, "error_code": STR, "error_msg": STR, "latency_ms": INT, "checked_at": TS,
    }),
    "detection-job": dict(required=["id", "status"], properties={
        "id": ID, "job_id": ID, "job_no": STR, "credential_id": ID, "provider_id": ID,
        "status": {"type": "string", "enum": ENUMS["DetectionJobStatus"]},
        "trigger_type": {"type": ["string", "null"], "enum": ENUMS["TriggerType"] + [None]},
        "started_at": TS, "finished_at": TS, "total_score": NUM,
        "result": {"type": ["string", "null"], "enum": ENUMS["ReportResult"] + [None]},
        "confidence": {"type": ["string", "null"], "enum": ENUMS["Confidence"] + [None]},
        "cost_estimate_usd": DEC6, "cost_actual_usd": DEC6, "challenge_verified": BOOL,
        "error_code": STR, "error_msg": STR, "report_id": ID, "attempt_count": INT,
        "progress": {"type": ["object", "null"], "properties": {
            "percent": NUM, "finished": INT, "total": INT, "eta_minutes": NUM}},
        "created_at": TS, "updated_at": TS,
    }),
    "detection-result": dict(required=["probe_code", "status"], properties={
        "probe_code": {"type": "string", "pattern": "^D[1-8]$"}, "probe_name": STR,
        "status": {"type": "string", "enum": ENUMS["ProbeStatus"]},
        "score": NUM, "weight_original": NUM, "weight_used": NUM,
        "metrics": {"type": ["object", "null"], "additionalProperties": True},
        "evidence": {}, "explanation": STR, "detail": STR, "attempt_count": INT,
    }),
    "report-summary": dict(required=["id"], properties={
        "id": ID, "report_id": ID, "report_no": STR, "result": {"type": ["string", "null"],
                                                                "enum": ENUMS["ReportResult"] + [None]},
        "total_score": NUM, "confidence": STR, "detected_at": TS, "created_at": TS,
        "provider_code": STR, "credential_id": ID, "channel_name": STR,
    }),
    "report": dict(required=["id", "report_no"], properties={
        "id": ID, "report_id": ID, "report_no": STR, "job_id": ID, "credential_id": ID,
        "channel_name": STR, "total_score": NUM,
        "result": {"type": ["string", "null"], "enum": ENUMS["ReportResult"] + [None]},
        "confidence": STR, "confidence_label": STR, "pass_count": INT, "item_total": INT,
        "unmeasurable_count": INT, "veto_triggered": BOOL, "verdict": STR,
        "provider_name": STR, "provider_code": STR, "api_key_masked": STR, "api_key_mask": STR,
        "model_list": {"type": ["array", "null"], "items": {"type": "string"}},
        "detected_at": TS, "trigger_type": STR, "duration_text": STR, "duration_seconds": INT,
        "cost_estimate_usd": DEC6, "cost_actual_usd": DEC6,
        "key_metrics": {"type": ["array", "null"], "items": {"type": "object", "properties": {
            "key": STR, "label": STR, "value": STR, "unit": STR, "sub": STR, "tone": STR}}},
        "sections": {"type": ["array", "null"], "items": {"type": "object", "properties": {
            "code": STR, "name": STR, "avg": NUM, "scored": BOOL, "note": STR,
            "items": {"type": ["array", "null"], "items": {"type": "object", "properties": {
                "code": STR, "name": STR, "metric": STR, "score": NUM, "status": STR, "value": STR}}}}}},
        "dims": {"type": ["array", "null"], "items": {"type": "object", "properties": {
            "code": STR, "name": STR, "score": NUM}}},
        "detail": {"type": ["object", "null"], "properties": {
            "code": STR, "title": STR, "score": NUM,
            "lines": {"type": ["array", "null"], "items": {"type": "string"}}}},
        "findings": {"type": ["array", "null"], "items": {"type": "object", "properties": {
            "title": STR, "body": STR, "tone": STR}}},
        "evidence": {"type": ["array", "null"], "items": {"type": "object", "properties": {
            "key": STR, "value": STR}}},
        "disclaimer": STR, "veto_note": STR, "weight_note": STR,
    }),
    "report-export": dict(required=["url"], properties={
        "url": STR, "file_url": STR, "file_name": STR, "expire_at": TS}),
    "price-time-rule": dict(required=["peak_ranges"], properties={
        "tz": {"type": "string", "default": "Asia/Shanghai"}, "weekday_scope": {"type": "string",
                                                                                "enum": ENUMS["WeekdayScope"]},
        "peak_ranges": {"type": "array", "items": {"type": "object", "required": ["start", "end"],
                                                   "properties": {"start": {"type": "string", "pattern": "^([01]\\d|2[0-3]):[0-5]\\d$"},
                                                                  "end": {"type": "string", "pattern": "^([01]\\d|2[0-3]):[0-5]\\d$"}}}},
        "peak_multiplier": {"type": ["number", "string", "null"]},
        "offpeak_multiplier": {"type": ["number", "string", "null"]},
        "peak_price_override": DEC6,
    }),
    "price-tier": dict(properties={
        "seq": INT, "min": DEC6, "min_value": DEC6, "max": DEC6, "max_value": DEC6, "label": STR,
        "input_price": DEC6, "output_price": DEC6, "cache_read_price": DEC6, "multiplier": NUM,
    }),
    "price-tier-rule": dict(required=["tier_field", "price_strategy", "tiers"], properties={
        "tier_field": {"type": "string", "enum": ENUMS["TierField"]},
        "price_strategy": {"type": "string", "enum": ENUMS["PriceStrategy"]},
        "tiers": {"type": "array", "items": {"$ref": "price-tier.schema.json"}},
    }),
    "request-rule": dict(properties={"when": STR, "when_expr": STR, "multiplier": NUM, "enabled": BOOL}),
    "quote-item": dict(required=["item_id", "quote_id", "model_name"], properties={
        "item_id": ID, "id": ID, "quote_id": ID, "quoteId": ID, "model_name": STR, "modelName": STR,
        "model_alias": STR, "input_price": DEC6, "output_price": DEC6, "cache_read_price": DEC6,
        "cache_write_price": DEC6, "cache_write_1h_price": DEC6, "image_input_price": DEC6,
        "audio_input_price": DEC6, "image_output_price": DEC6, "audio_output_price": DEC6,
        "tier": STR, "billing_mode": STR, "compile_status": STR, "note": STR,
        "time_rule": {"oneOf": [{"$ref": "price-time-rule.schema.json"}, {"type": "null"}]},
        "tier_rule": {"oneOf": [{"$ref": "price-tier-rule.schema.json"}, {"type": "null"}]},
        "request_rules": {"type": ["array", "null"], "items": {"$ref": "request-rule.schema.json"}},
        "created_at": TS, "updated_at": TS, "version": INT,
    }),
    "quote-row": dict(required=["id"], properties={
        "id": ID, "quote_id": ID, "title": STR, "name": STR, "quote_no": STR,
        "status": {"type": ["string", "null"], "enum": ENUMS["QuoteStatus"] + [None]},
        "currency": STR, "item_count": INT, "items": {"type": ["array", "null"], "items": {"type": "object"}},
        "amount_total": DEC6, "updated_at": TS, "created_at": TS, "contract_id": ID,
        "valid_from": TS, "valid_to": TS, "credential_id": ID,
    }),
    "quote-detail": dict(required=["quote_id", "status"], properties={
        "quote_id": ID, "id": ID, "quote_no": STR, "name": STR, "title": STR,
        "provider_id": ID, "credential_id": ID,
        "status": {"type": "string", "enum": ENUMS["QuoteStatus"]},
        "current_version": INT, "currency": STR, "valid_from": TS, "valid_to": TS, "item_count": INT,
        "remark": STR, "reject_reason_code": STR, "reject_reason_text": STR,
        "submitted_at": TS, "reviewed_at": TS, "contract_id": ID, "source_hash": STR,
        "item_total": INT,
        "items": {"type": ["array", "null"], "items": {"$ref": "quote-item.schema.json"}},
        "amount_total": DEC6, "updated_at": TS, "created_at": TS, "version": INT,
    }),
    "quote-version": dict(properties={
        "id": ID, "quote_id": ID, "version_no": INT, "snapshot": {"type": ["object", "null"]},
        "source_hash": STR, "created_at": TS}),
    "verify-case": dict(properties={
        "case_code": STR, "case_name": STR, "input": {"type": ["object", "null"]}, "expected": DEC6,
        "actual": DEC6, "passed": BOOL, "diff_note": STR}),
    "verify-report": dict(properties={
        "status": STR, "case_total": INT, "case_passed": INT, "failed_field": STR,
        "cases": {"type": ["array", "null"], "items": {"$ref": "verify-case.schema.json"}},
        "started_at": TS, "finished_at": TS}),
    "model-expression": dict(required=["model_name", "expr"], properties={
        "model_name": STR, "expr_version": STR, "expr": STR,
        "tier_labels": {"type": ["array", "null"], "items": {"type": "string"}},
        "rule_hits": {"type": ["array", "null"], "items": {"type": "string"}},
        "verified": BOOL, "source_hash": STR, "inline_expanded": STR}),
    "compilation-result": dict(required=["compilation_id", "gate_status"], properties={
        "compilation_id": ID, "id": ID, "quote_id": ID, "quote_version": INT, "provider_id": ID,
        "status": STR, "gate_status": STR, "source_hash": STR, "compiler_version": STR,
        "publish_blocked": BOOL, "previous_expr": {"type": ["object", "null"]},
        "compiled": {"type": ["array", "null"], "items": {"$ref": "model-expression.schema.json"}},
        "verify_report": {"oneOf": [{"$ref": "verify-report.schema.json"}, {"type": "null"}]},
        "confirmed_at": TS, "created_at": TS,
    }),
    "quote-compare": dict(properties={
        "model_name": STR, "field": STR, "old_value": DEC6, "new_value": DEC6, "change_rate": NUM}),
    "review-task": dict(required=["id", "status"], properties={
        "id": ID, "review_id": ID, "quote_id": ID, "quote_no": STR, "provider_id": ID, "provider_name": STR,
        "status": STR, "claimed_by": ID, "claimed_at": TS, "review_comment": STR,
        "reject_reason_code": {"type": ["string", "null"], "enum": ENUMS["QuoteRejectReason"] + [None]},
        "tech_metrics_snapshot": {"type": ["object", "null"]}, "created_at": TS, "updated_at": TS}),
    "review-record": dict(properties={
        "id": ID, "quote_id": ID, "task_id": ID, "action": STR, "operator_id": ID,
        "before_status": STR, "after_status": STR, "comment": STR, "created_at": TS}),
    "contract": dict(required=["id", "contract_no", "status"], properties={
        "id": ID, "contract_id": ID, "contract_no": STR, "quote_id": ID, "provider_id": ID,
        "title": STR, "name": STR, "contract_name": STR,
        "status": {"type": "string", "enum": ENUMS["ContractStatus"]},
        "sign_channel": STR, "cooperation_mode": STR, "mode": STR,
        "valid_from": TS, "valid_to": TS, "effective_from": TS, "effective_to": TS,
        "settlement_cycle": STR, "fee_rate": STR, "platform_fee_rate": NUM, "currency": STR,
        "settlement_currency": STR, "min_settlement_amount": NUM, "min_amount": NUM,
        "sign_deadline": TS, "deadline": TS, "expire_sign_at": TS,
        "supplier_name": STR, "company_name": STR,
        "signer_name": STR, "signer": STR, "signer_phone_masked": STR, "phone_masked": STR,
        "sign_method": STR,
        "terms": {"type": ["array", "null"], "items": {"type": "string"}},
        "clauses": {"type": ["array", "null"], "items": {"type": "string"}},
        "records": {"type": ["array", "null"], "items": {"type": "object", "properties": {
            "title": STR, "time": STR, "tone": STR, "at": TS, "signer_type": STR, "sign_method": STR}}},
        "file_id": ID, "file_url": STR, "file_name": STR, "signed_at": TS, "archived_at": TS,
        "created_at": TS, "updated_at": TS, "version": INT,
    }),
    "payment": dict(required=["id"], properties={
        "id": ID, "payment_id": ID, "provider_id": ID, "contract_id": ID,
        "amount": DEC6, "currency": STR,
        "status": {"type": ["string", "null"], "enum": ENUMS["PaymentStatus"] + [None]},
        "voucher_file_id": ID, "paid_at": TS, "confirmed_at": TS, "remark": STR, "created_at": TS,
        "available_balance": DEC6, "pending_settlement": DEC6, "total_settled": DEC6}),
    "settlement-statement": dict(required=["id"], properties={
        "id": ID, "statement_no": STR, "provider_id": ID, "period_from": TS, "period_to": TS,
        "total_amount": DEC6, "platform_fee": DEC6, "status": STR, "created_at": TS}),
    "notification": dict(required=["id"], properties={
        "id": ID, "title": STR, "content": STR, "created_at": TS, "read_at": TS,
        "read": BOOL, "is_read": BOOL, "event_code": STR, "biz_type": STR, "biz_id": ID,
        "channel": STR, "category": STR, "kind": STR, "status": STR}),
    "notification-read": dict(required=["id"], properties={"id": ID, "read_at": TS}),
    "usage-model": dict(required=["model_name"], properties={
        "model_name": {"type": "string"}, "request_count": INT, "total_tokens": TOKENS,
        "amount": DEC6, "share": NUM, "percent": NUM}),
    "usage-daily": dict(properties={
        "stat_date": {"type": ["string", "null"], "format": "date"}, "date": STR, "day": STR,
        "total_tokens": TOKENS, "tokens": TOKENS, "amount": DEC6, "request_count": INT}),
    "usage-cost": dict(properties={
        "input": DEC6, "input_cost": DEC6, "output": DEC6, "output_cost": DEC6,
        "platform_fee": DEC6, "platform_fee_rate": NUM, "total": DEC6, "total_cost": DEC6}),
    "usage-summary": dict(required=["provider_id"], properties={
        "provider_id": ID, "stat_from": TS, "stat_to": TS, "month": STR,
        "request_count": INT, "prompt_tokens": TOKENS, "completion_tokens": TOKENS, "total_tokens": TOKENS,
        "cache_read_tokens": TOKENS, "cache_write_tokens": TOKENS, "cache_write_1h_tokens": TOKENS,
        "image_input_tokens": TOKENS, "audio_input_tokens": TOKENS, "video_input_tokens": TOKENS,
        "cache_hit_rate": NUM, "cache_parse_rate": NUM, "quota_raw": DEC6, "cost_usd": DEC6,
        "amount_total": DEC6, "amount": DEC6, "mom_rate": NUM, "mom_saved_amount": DEC6,
        "actual_unit_price": DEC6, "deviation_rate": NUM,
        "tier_distribution": {"type": ["object", "null"], "additionalProperties": {"type": "number"}},
        "models": {"type": ["array", "null"], "items": {"$ref": "usage-model.schema.json"}},
        "daily": {"type": ["array", "null"], "items": {"$ref": "usage-daily.schema.json"}},
        "cost": {"oneOf": [{"$ref": "usage-cost.schema.json"}, {"type": "null"}]},
        "cost_breakdown": {"oneOf": [{"$ref": "usage-cost.schema.json"}, {"type": "null"}]},
        "updated_at": TS, "refreshed_at": TS, "degraded": BOOL,
    }),
    "usage-hourly-bucket": dict(required=["stat_hour"], properties={
        "stat_hour": TS, "channel_id": ID, "channel_name": STR, "provider_id": ID,
        "model_name": STR, "group_name": STR, "request_count": INT,
        "prompt_tokens": TOKENS, "completion_tokens": TOKENS, "total_tokens": TOKENS,
        "cache_read_tokens": TOKENS, "cache_write_tokens": TOKENS, "cache_write_1h_tokens": TOKENS,
        "image_input_tokens": TOKENS, "audio_input_tokens": TOKENS, "video_input_tokens": TOKENS,
        "quota_raw": DEC6, "cost_usd": DEC6,
        "cache_parse_status": {"type": ["string", "null"], "enum": ENUMS["CacheParseStatus"] + [None]},
        "source": STR, "tier_distribution": {"type": ["object", "null"]}, "collected_at": TS}),
    "usage-refresh-result": dict(required=["batch_id"], properties={
        "batch_id": ID, "inserted": INT, "updated": INT, "batch_total": INT,
        "cache_parse_status": STR, "from": TS, "to": TS}),
    "channel-binding": dict(required=["id"], properties={
        "id": ID, "binding_id": ID, "provider_id": ID, "credential_id": ID, "endpoint_id": ID,
        "channel_id": INT, "channel_name": STR, "tag": STR, "group_name": STR,
        "priority": INT, "weight": INT, "models": {"type": ["array", "null"], "items": {"type": "string"}},
        "status": {"type": ["string", "null"], "enum": ENUMS["SyncStatus"] + [None]},
        "last_synced_at": TS, "last_readback_hash": STR}),
    "sync-operation": dict(properties={
        "id": ID, "operation": STR, "request_payload": {"type": ["object", "null"]},
        "response_payload": {"type": ["object", "null"]}, "result": STR, "readback_equal": BOOL,
        "attempt_no": INT, "error": STR, "created_at": TS}),
    "sync-task": dict(required=["id", "status"], properties={
        "id": ID, "task_id": ID, "task_no": STR, "binding_id": ID, "provider_id": ID,
        "compilation_id": ID, "task_type": STR, "status": STR, "payload": {"type": ["object", "null"]},
        "idempotency_key": STR, "attempt_count": INT, "next_retry_at": TS, "last_error": STR,
        "readback_equal": BOOL, "operations": {"type": ["array", "null"],
                                               "items": {"$ref": "sync-operation.schema.json"}},
        "created_at": TS, "updated_at": TS}),
    "model-info": dict(properties={"model_name": STR, "vendor": STR, "owned_by": STR, "enabled": BOOL}),
    "detection-config-probe": dict(properties={
        "probe_code": STR, "probe_name": STR, "enabled": BOOL, "weight": NUM,
        "timeout_seconds": INT, "params": {"type": ["object", "null"]}}),
    "detection-config": dict(required=["id"], properties={
        "id": ID, "config_id": ID, "version_no": STR, "name": STR, "pass_score": INT,
        "veto_rule": {"type": ["object", "null"]}, "status": STR,
        "probes": {"type": ["array", "null"], "items": {"$ref": "detection-config-probe.schema.json"}},
        "published_at": TS, "created_at": TS, "updated_at": TS}),
    "report-template": dict(required=["id"], properties={
        "id": ID, "template_id": ID, "template_no": STR, "version_no": STR, "title": STR,
        "logo_file_id": ID, "section_order": {"type": ["array", "null"], "items": {"type": "string"}},
        "disclaimer": STR, "status": STR, "published_at": TS, "created_at": TS}),
    "audit-log": dict(required=["id", "action"], properties={
        "id": ID, "trace_id": STR, "actor_type": STR, "actor_id": ID, "actor_name": STR,
        "actor_ip": STR, "user_agent": STR,
        "action": {"type": "string", "enum": ENUMS["AuditAction"]},
        "target_type": STR, "target_id": ID, "summary": STR,
        "before_value": {"type": ["object", "null"]}, "after_value": {"type": ["object", "null"]},
        "result": STR, "risk_level": STR, "created_at": TS}),
    "login-result": dict(required=["token", "role"], properties={
        "token": STR, "refresh_token": STR, "refreshToken": STR,
        "role": {"type": "string", "enum": ENUMS["Role"]},
        "providerId": ID, "provider_id": ID, "providerCode": STR, "provider_code": STR,
        "status": STR, "expires_in": INT}),
    "me-result": dict(required=["role"], properties={
        "phone": STR, "phone_masked": STR, "masked": STR, "role": {"type": "string", "enum": ENUMS["Role"]},
        "providerId": ID, "provider_id": ID, "providerCode": STR, "provider_code": STR,
        "status": STR, "nickname": STR, "wechat_bound": BOOL, "sms_2fa": BOOL,
        "wechat_subscribed": BOOL, "login_security": STR, "subscribed": BOOL}),
    "sms-send-result": dict(required=["ttl"], properties={"ttl": {"type": "integer"}, "expire_at": TS}),
    "qualification-created": dict(required=["id"], properties={
        "id": ID, "qualification_id": ID, "category": STR, "file_name": STR, "file_size": INT,
        "status": STR, "detection_job_id": ID, "uploaded_at": TS}),
    "job-created": dict(required=["job_id", "status"], properties={
        "job_id": ID, "id": ID, "job_no": STR, "status": STR, "credential_id": ID}),
    "precheck-result": dict(required=["job_id"], properties={
        "job_id": ID, "detection_job_id": ID, "status": STR, "precheck_status": STR}),
    "reveal-result": dict(required=["api_key"], properties={"api_key": STR, "expire_at": TS}),
}

# ---------------------------------------------------------------- requests
REQUESTS: dict[str, dict] = {
    "auth-sms-send": dict(required=["phone", "captcha"], properties={
        "phone": {"type": "string", "pattern": "^1[3-9]\\d{9}$"}, "captcha": {"type": "string"}}),
    "auth-sms-login": dict(required=["phone", "smsCode"], properties={
        "phone": {"type": "string", "pattern": "^1[3-9]\\d{9}$"},
        "smsCode": {"type": "string", "pattern": "^\\d{6}$"}}),
    "auth-wechat-login": dict(required=["code"], properties={"code": {"type": "string", "minLength": 1}}),
    "auth-refresh": dict(required=["refreshToken"], properties={"refreshToken": {"type": "string"}}),
    "provider-profile-update": dict(properties={
        "short_name": {"type": "string", "maxLength": 64},
        "company_name": {"type": "string", "maxLength": 128},
        "uscc": {"type": "string", "pattern": "^[0-9A-Z]{18}$"},
        "industry_category": {"type": "string", "enum": ENUMS["IndustryCategory"]},
        "province": STR, "city": STR, "address": STR, "website": STR,
        "contact_name": STR, "contact_title": STR,
        "contact_phone": {"type": ["string", "null"], "pattern": "^1[3-9]\\d{9}$"},
        "contact_email": STR, "company_intro": STR,
        "recheck_interval_days": {"type": ["integer", "null"], "minimum": 1, "maximum": 365}}),
    "qualification-create": dict(required=["category", "file_name"], properties={
        "category": {"type": "string", "enum": ["BUSINESS_LICENSE", "AUTHORIZATION", "OTHER"]},
        "file_name": {"type": "string", "maxLength": 255},
        "file_size": {"type": ["integer", "null"], "maximum": 10485760},
        "content_type": STR, "file_id": ID,
        "company_name": STR, "uscc": STR,
        "contact_name": STR, "contact_phone": STR, "remark": STR}),
    "credential-create": dict(required=["base_url", "api_key"], properties={
        "alias": {"type": ["string", "null"], "minLength": 2, "maxLength": 64},
        "base_url": {"type": "string", "format": "uri"},
        "api_key": {"type": "string", "minLength": 8},
        "primary_flag": BOOL, "is_primary": BOOL,
        "declared_vendor": STR, "declared_rpm": INT, "declared_tpm": INT, "declared_context_window": INT,
        "env_tag": STR,
        "model_list": {"type": ["array", "null"], "items": {"$ref": "model-entry.schema.json"}}}),
    "credential-reveal": dict(required=["smsCode"], properties={"smsCode": {"type": "string", "pattern": "^\\d{6}$"}}),
    "detection-job-create": dict(required=["credential_id"], properties={
        "credential_id": ID, "trigger_type": {"type": ["string", "null"], "enum": ENUMS["TriggerType"] + [None]}}),
    "detection-release": dict(required=["override_reason"], properties={
        "override_reason": {"type": "string", "minLength": 2, "maxLength": 500}}),
    "quote-create": dict(required=["name", "credential_id"], properties={
        "name": {"type": "string", "minLength": 1, "maxLength": 64},
        "provider_id": ID, "credential_id": ID, "remark": STR,
        "currency": {"type": ["string", "null"], "enum": ["USD", None]},
        "valid_from": TS, "valid_to": TS}),
    "quote-items-create": dict(required=["items"], properties={
        "items": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["model_name"],
                                                            "properties": {"model_name": {"type": "string"},
                                                                           "model_alias": STR}}}}),
    "quote-item-save": dict(properties={
        "model_alias": STR,
        "input_price": {"type": ["number", "null"], "minimum": 0},
        "output_price": {"type": ["number", "null"], "minimum": 0},
        "cache_read_price": {"type": ["number", "null"], "minimum": 0},
        "cache_write_price": {"type": ["number", "null"], "minimum": 0},
        "cache_write_1h_price": {"type": ["number", "null"], "minimum": 0},
        "image_input_price": {"type": ["number", "null"], "minimum": 0},
        "audio_input_price": {"type": ["number", "null"], "minimum": 0},
        "image_output_price": {"type": ["number", "null"], "minimum": 0},
        "audio_output_price": {"type": ["number", "null"], "minimum": 0},
        "note": STR, "tier": STR, "billing_mode": STR,
        "time_rule": {"oneOf": [{"$ref": "price-time-rule.schema.json"}, {"type": "null"}]},
        "tier_rule": {"oneOf": [{"$ref": "price-tier-rule.schema.json"}, {"type": "null"}]},
        "request_rules": {"type": ["array", "null"], "items": {"$ref": "request-rule.schema.json"}},
    }),
    "quote-submit": dict(properties={}),
    "contract-sign": dict(properties={
        "sign_method": {"type": ["string", "null"], "enum": ["SMS", "SEAL", None]},
        "smsCode": {"type": ["string", "null"], "pattern": "^\\d{6}$"}}),
    "review-reject": dict(required=["reason_code"], properties={
        "reason_code": {"type": "string", "enum": ENUMS["QuoteRejectReason"]},
        "reason_text": {"type": ["string", "null"], "minLength": 2, "maxLength": 500},
        "item_id": ID, "field": STR}),
    "review-approve": dict(properties={"comment": {"type": ["string", "null"], "maxLength": 500}}),
    "contract-issue": dict(required=["file_id"], properties={
        "file_id": ID, "valid_from": TS, "valid_to": TS,
        "cooperation_mode": STR, "settlement_cycle": STR,
        "platform_fee_rate": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        "currency": STR, "min_settlement_amount": DEC6,
        "terms": {"type": ["array", "null"], "items": {"type": "string"}},
        "sign_deadline": TS}),
    "payment-record": dict(required=["provider_id", "contract_id", "amount"], properties={
        "provider_id": ID, "contract_id": ID, "amount": {"type": "number", "minimum": 0.000001},
        "currency": {"type": ["string", "null"], "enum": ["USD", None]},
        "voucher_file_id": ID, "remark": STR}),
    "provider-suspend": dict(required=["suspend_reason"], properties={
        "suspend_reason": {"type": "string", "minLength": 2, "maxLength": 500}}),
    "binding-status": dict(required=["target_status"], properties={
        "target_status": {"type": "string", "enum": ["ENABLED", "DISABLED"]}}),
    "usage-refresh": dict(properties={"from": TS, "to": TS, "batch_id": ID}),
    "detection-config-save": dict(required=["name"], properties={
        "name": {"type": "string", "maxLength": 64},
        "pass_score": {"type": ["integer", "null"], "minimum": 0, "maximum": 100},
        "veto_rule": {"type": ["object", "null"]}, "status": STR,
        "probes": {"type": ["array", "null"], "items": {"$ref": "detection-config-probe.schema.json"}}}),
    "report-template-save": dict(required=["title"], properties={
        "title": {"type": "string", "maxLength": 128}, "logo_file_id": ID,
        "section_order": {"type": ["array", "null"], "items": {"type": "string"}},
        "disclaimer": STR, "status": STR}),
}

# ---------------------------------------------------------------- paths
# (id, method, path, tag, roles, request_schema|None, response_model|None, params, errors, note)
PATHS: list[tuple] = [
    ("AUTH-01", "post", "/auth/sms/send", "Auth", "anon", "auth-sms-send", "sms-send-result", [], ["E-1001", "E-1903"], "真源"),
    ("AUTH-02", "post", "/auth/sms/login", "Auth", "anon", "auth-sms-login", "login-result", [], ["E-1001", "E-1101", "E-1903"], "真源"),
    ("AUTH-03", "post", "/auth/wechat/login", "Auth", "anon", "auth-wechat-login", "login-result", [], ["E-1001"], "真源"),
    ("AUTH-04", "post", "/auth/refresh", "Auth", "anon", "auth-refresh", "login-result", [], ["E-1902"], "推断"),
    ("AUTH-05", "post", "/auth/logout", "Auth", "authenticated", None, None, [], [], "真源"),
    ("AUTH-06", "get", "/auth/me", "Auth", "authenticated", None, "me-result", [], ["E-1902"], "真源+约定"),
    ("PROV-01", "get", "/provider/profile", "Provider", "PROVIDER", None, "provider-profile", [], ["E-1101"], "真源"),
    ("PROV-02", "put", "/provider/profile", "Provider", "PROVIDER", "provider-profile-update", "provider-profile", [], ["E-1001", "E-1104", "E-1601"], "真源+约定"),
    ("PROV-03", "get", "/provider/qualifications", "Provider", "PROVIDER", None, "provider-qualification", ["page", "pageSize"], [], "真源"),
    ("PROV-04", "post", "/provider/qualifications", "Provider", "PROVIDER", "qualification-create", "qualification-created", [], ["E-1001"], "真源"),
    ("PROV-05", "delete", "/provider/qualifications/{id}", "Provider", "PROVIDER", None, None, [], ["E-1901", "E-2001"], "真源"),
    ("CRED-01", "get", "/credentials", "Credential", "PROVIDER", None, "credential-row", ["page", "pageSize", "status"], [], "真源"),
    ("CRED-02", "post", "/credentials", "Credential", "PROVIDER", "credential-create", "credential-detail", [], ["E-1001", "E-1104", "E-1201"], "推断"),
    ("CRED-03", "get", "/credentials/{id}", "Credential", "PROVIDER", None, "credential-detail", [], ["E-1901"], "真源"),
    ("CRED-04", "put", "/credentials/{id}", "Credential", "PROVIDER", "credential-create", "credential-detail", [], ["E-1001", "E-1104", "E-1601"], "真源"),
    ("CRED-05", "post", "/credentials/{id}/precheck", "Credential", "PROVIDER", None, "precheck-result", [], ["E-1101", "E-1201", "E-1301"], "真源"),
    ("CRED-06", "get", "/credentials/{id}/precheck/latest", "Credential", "PROVIDER", None, "credential-precheck", [], ["E-1101"], "推断"),
    ("CRED-07", "post", "/credentials/{id}/reveal", "Credential", "SUPER_ADMIN", "credential-reveal", "reveal-result", [], ["E-1901", "E-1902"], "真源"),
    ("DET-01", "post", "/detection-jobs", "Detection", "PROVIDER", "detection-job-create", "job-created", [], ["E-1301", "E-1302", "E-1303"], "真源"),
    ("DET-02", "get", "/detection-jobs/{jobId}", "Detection", "PROVIDER", None, "detection-job", [], ["E-1304"], "真源"),
    ("DET-03", "get", "/detection-jobs/{jobId}/results", "Detection", "PROVIDER", None, "detection-result", [], ["E-1304"], "真源"),
    ("DET-04", "get", "/detection-jobs/{jobId}/results/{probeCode}", "Detection", "PROVIDER", None, "detection-result", [], ["E-1304"], "推断"),
    ("DET-05", "post", "/detection-jobs/{jobId}/cancel", "Detection", "PROVIDER", None, "detection-job", [], ["E-1305", "E-1601"], "推断"),
    ("DET-06", "post", "/detection-jobs/{jobId}/release", "Detection", "TECH_OPS,SUPER_ADMIN", "detection-release", "detection-job", [], ["E-1601"], "真源"),
    ("RPT-01", "get", "/reports", "Report", "PROVIDER", None, "report-summary", ["page", "pageSize", "result"], [], "真源"),
    ("RPT-02", "get", "/reports/{reportId}", "Report", "PROVIDER", None, "report", [], ["E-1401"], "真源"),
    ("RPT-03", "get", "/reports/{reportId}/html", "Report", "PROVIDER", None, None, [], ["E-1401"], "推断"),
    ("RPT-04", "get", "/reports/{reportId}/export", "Report", "PROVIDER", None, "report-export", [], ["E-1401"], "真源"),
    ("QT-01", "get", "/quotes", "Quote", "PROVIDER", None, "quote-row", ["page", "pageSize", "status"], [], "真源"),
    ("QT-02", "post", "/quotes", "Quote", "PROVIDER", "quote-create", "quote-detail", [], ["E-1602", "E-1001"], "真源"),
    ("QT-03", "get", "/quotes/{quoteId}", "Quote", "PROVIDER", None, "quote-detail", [], ["E-1401"], "真源"),
    ("QT-04", "delete", "/quotes/{quoteId}", "Quote", "PROVIDER", None, "quote-detail", [], ["E-1601"], "真源"),
    ("QT-05", "post", "/quotes/{quoteId}/items", "Quote", "PROVIDER", "quote-items-create", "quote-detail", [], ["E-1001", "E-1401"], "真源"),
    ("QT-06", "get", "/quotes/{quoteId}/items", "Quote", "PROVIDER", None, "quote-item", ["page", "pageSize"], [], "真源"),
    ("QT-07", "get", "/quotes/items/{itemId}", "Quote", "PROVIDER", None, "quote-item", [], ["E-1401"], "真源"),
    ("QT-08", "put", "/quotes/items/{itemId}", "Quote", "PROVIDER", "quote-item-save", "quote-item", [], ["E-1001", "E-1401", "E-1402", "E-1403"], "真源"),
    ("QT-09", "post", "/quotes/{quoteId}/submit", "Quote", "PROVIDER", "quote-submit", "quote-detail", [], ["E-1001", "E-1401", "E-1402", "E-1601", "E-1602"], "真源"),
    ("QT-10", "post", "/quotes/{quoteId}/withdraw", "Quote", "PROVIDER", None, "quote-detail", [], ["E-1601"], "真源"),
    ("QT-11", "get", "/quotes/{quoteId}/versions", "Quote", "PROVIDER", None, "quote-version", ["page", "pageSize"], [], "推断"),
    ("QT-12", "post", "/quotes/{quoteId}/compile-preview", "Quote", "PROVIDER", None, "compilation-result", [], ["E-1401", "E-1402", "E-1405"], "真源"),
    ("CON-01", "get", "/contracts", "Contract", "PROVIDER", None, "contract", ["page", "pageSize", "status"], [], "真源"),
    ("CON-02", "get", "/contracts/{id}", "Contract", "PROVIDER", None, "contract", [], ["E-1701"], "真源"),
    ("CON-03", "get", "/contracts/{id}/file", "Contract", "PROVIDER", None, "report-export", [], ["E-1701"], "真源"),
    ("CON-04", "post", "/contracts/{id}/sign", "Contract", "PROVIDER", "contract-sign", "contract", [], ["E-1701", "E-1601"], "真源"),
    ("PAY-01", "get", "/payments", "Payment", "PROVIDER", None, "payment", ["page", "pageSize"], [], "真源+约定"),
    ("NTF-01", "get", "/notifications", "Notification", "authenticated", None, "notification", ["page", "pageSize", "unread", "category"], [], "真源+推断"),
    ("NTF-02", "post", "/notifications/{id}/read", "Notification", "authenticated", None, "notification-read", [], ["E-1901"], "真源"),
    ("USE-01", "get", "/usage/summary", "Usage", "PROVIDER", None, "usage-summary", ["startHour", "endHour", "month"], ["E-1801"], "真源"),
    ("USE-02", "get", "/usage/hourly", "Usage", "PROVIDER", None, "usage-hourly-bucket", ["from", "to", "model", "group", "page", "pageSize"], ["E-1801"], "真源"),
    # 管理端账号接入（2026-09-23 新增）：此前管理端没有登录入口 —— aap-admin 调供应商 AUTH-02
    # 只会拿到 PROVIDER 身份 → /admin/** 全 403。见 docs/backend/02-API接口模型清单.md §2.5。
    ("ADM-AUTH01", "post", "/admin/auth/sms/login", "AdminAuth", "anon", "auth-sms-login", "login-result", [], ["E-1001", "E-1901", "E-1902", "E-1903"], "新增"),
    ("ADM-P01", "get", "/admin/providers", "Admin", "BIZ_OPERATOR,TECH_OPS,SUPER_ADMIN", None, "provider-profile", ["page", "pageSize", "status", "keyword"], [], "推断"),
    ("ADM-P02", "post", "/admin/providers/{id}/suspend", "Admin", "BIZ_OPERATOR,TECH_OPS,SUPER_ADMIN", "provider-suspend", "provider-profile", [], ["E-1601"], "真源"),
    ("ADM-P03", "post", "/admin/providers/{id}/resume", "Admin", "BIZ_OPERATOR,TECH_OPS,SUPER_ADMIN", None, "provider-profile", [], ["E-1601"], "真源"),
    ("ADM-C01", "get", "/admin/credentials/{id}", "Admin", "SUPER_ADMIN", None, "credential-detail", [], ["E-1901"], "推断"),
    ("ADM-C02", "post", "/admin/credentials/{id}/reveal", "Admin", "SUPER_ADMIN", "credential-reveal", "reveal-result", [], ["E-1901", "E-1902"], "真源"),
    ("ADM-Q01", "post", "/admin/quotes/{id}/compile", "Admin", "TECH_OPS,SUPER_ADMIN", None, "compilation-result", [], ["E-1401", "E-1402", "E-1405"], "真源"),
    ("ADM-Q02", "get", "/admin/quotes/compare", "Admin", "BIZ_OPERATOR,SUPER_ADMIN", None, "quote-compare", ["quoteIds"], [], "推断"),
    ("ADM-CP01", "get", "/admin/compilations", "Admin", "TECH_OPS,SUPER_ADMIN", None, "compilation-result", ["page", "pageSize", "status"], [], "真源"),
    ("ADM-CP02", "get", "/admin/compilations/{id}", "Admin", "TECH_OPS,SUPER_ADMIN", None, "compilation-result", [], ["E-1406"], "真源"),
    ("ADM-CP03", "post", "/admin/compilations/{id}/verify", "Admin", "TECH_OPS,SUPER_ADMIN", None, "verify-report", [], ["E-1405"], "真源"),
    ("ADM-CP04", "post", "/admin/compilations/{id}/confirm", "Admin", "TECH_OPS,SUPER_ADMIN", None, "compilation-result", [], ["E-1405", "E-1407"], "真源"),
    ("ADM-R01", "get", "/admin/reviews", "Admin", "BIZ_OPERATOR,TECH_OPS,SUPER_ADMIN", None, "review-task", ["page", "pageSize", "status"], [], "真源"),
    ("ADM-R02", "post", "/admin/reviews/{id}/claim", "Admin", "BIZ_OPERATOR,SUPER_ADMIN", None, "review-task", [], ["E-1601"], "真源"),
    ("ADM-R03", "post", "/admin/reviews/{id}/approve", "Admin", "BIZ_OPERATOR,SUPER_ADMIN", "review-approve", "review-task", [], ["E-1601"], "真源"),
    ("ADM-R04", "post", "/admin/reviews/{id}/reject", "Admin", "BIZ_OPERATOR,SUPER_ADMIN", "review-reject", "review-task", [], ["E-1001", "E-1601"], "真源"),
    ("ADM-R05", "get", "/admin/reviews/records", "Admin", "BIZ_OPERATOR,TECH_OPS,SUPER_ADMIN", None, "review-record", ["quoteId", "page", "pageSize"], [], "推断"),
    ("ADM-CT01", "get", "/admin/contracts", "Admin", "BIZ_OPERATOR,SUPER_ADMIN", None, "contract", ["page", "pageSize", "status"], [], "真源"),
    ("ADM-CT02", "post", "/admin/contracts/{id}/issue", "Admin", "BIZ_OPERATOR,SUPER_ADMIN", "contract-issue", "contract", [], ["E-1001", "E-1601"], "真源"),
    ("ADM-CT03", "post", "/admin/contracts/{id}/confirm-sign", "Admin", "BIZ_OPERATOR,SUPER_ADMIN", None, "contract", [], ["E-1601"], "真源"),
    ("ADM-PAY01", "get", "/admin/payments", "Admin", "BIZ_OPERATOR,SUPER_ADMIN", None, "payment", ["page", "pageSize", "status"], [], "真源"),
    ("ADM-PAY02", "post", "/admin/payments/{id}/confirm", "Admin", "BIZ_OPERATOR,SUPER_ADMIN", None, "payment", [], ["E-1601", "E-1701"], "真源"),
    ("ADM-PAY03", "get", "/admin/settlements", "Admin", "BIZ_OPERATOR,SUPER_ADMIN", None, "settlement-statement", ["page", "pageSize"], [], "真源"),
    ("ADM-S01", "get", "/admin/sync/tasks", "Admin", "TECH_OPS,SUPER_ADMIN", None, "sync-task", ["page", "pageSize", "status", "bindingId"], [], "真源"),
    ("ADM-S02", "get", "/admin/sync/tasks/{taskId}", "Admin", "TECH_OPS,SUPER_ADMIN", None, "sync-task", [], ["E-1501"], "真源"),
    ("ADM-S03", "post", "/admin/sync/tasks/{taskId}/retry", "Admin", "TECH_OPS,SUPER_ADMIN", None, "sync-task", [], ["E-1501", "E-1505"], "真源"),
    ("ADM-S04", "get", "/admin/channel-bindings", "Admin", "TECH_OPS,SUPER_ADMIN", None, "channel-binding", ["page", "pageSize"], [], "推断"),
    ("ADM-S05", "post", "/admin/channel-bindings/{bindingId}/status", "Admin", "TECH_OPS,SUPER_ADMIN", "binding-status", "channel-binding", [], ["E-1505"], "真源"),
    ("ADM-S06", "get", "/admin/sync/models/upstream", "Admin", "TECH_OPS,SUPER_ADMIN", None, "model-info", [], ["E-1505"], "真源"),
    ("ADM-U01", "get", "/admin/usage/hourly", "Admin", "TECH_OPS,BIZ_OPERATOR,SUPER_ADMIN", None, "usage-hourly-bucket", ["from", "to", "providerId", "channelId", "model", "page", "pageSize"], ["E-1801"], "真源"),
    ("ADM-U02", "post", "/admin/usage/refresh", "Admin", "TECH_OPS,SUPER_ADMIN", "usage-refresh", "usage-refresh-result", [], ["E-1801"], "真源"),
    ("ADM-CFG01", "get", "/admin/detection-configs", "Admin", "TECH_OPS,SUPER_ADMIN", None, "detection-config", ["page", "pageSize"], [], "推断"),
    ("ADM-CFG02", "post", "/admin/detection-configs", "Admin", "TECH_OPS,SUPER_ADMIN", "detection-config-save", "detection-config", [], ["E-1001"], "推断"),
    ("ADM-CFG03", "get", "/admin/detection-configs/{configId}", "Admin", "TECH_OPS,SUPER_ADMIN", None, "detection-config", [], ["E-1406"], "推断"),
    ("ADM-CFG04", "put", "/admin/detection-configs/{configId}", "Admin", "TECH_OPS,SUPER_ADMIN", "detection-config-save", "detection-config", [], ["E-1601"], "推断"),
    ("ADM-CFG05", "post", "/admin/detection-configs/{configId}/publish", "Admin", "TECH_OPS,SUPER_ADMIN", None, "detection-config", [], ["E-1601"], "推断"),
    ("ADM-CFG06", "get", "/admin/report-templates", "Admin", "TECH_OPS,SUPER_ADMIN", None, "report-template", ["page", "pageSize"], [], "推断"),
    ("ADM-CFG07", "post", "/admin/report-templates", "Admin", "TECH_OPS,SUPER_ADMIN", "report-template-save", "report-template", [], ["E-1001"], "推断"),
    ("ADM-CFG08", "get", "/admin/report-templates/{templateId}", "Admin", "TECH_OPS,SUPER_ADMIN", None, "report-template", [], ["E-1406"], "推断"),
    ("ADM-CFG09", "put", "/admin/report-templates/{templateId}", "Admin", "TECH_OPS,SUPER_ADMIN", "report-template-save", "report-template", [], ["E-1601"], "推断"),
    ("ADM-CFG10", "post", "/admin/report-templates/{templateId}/publish", "Admin", "TECH_OPS,SUPER_ADMIN", None, "report-template", [], ["E-1601"], "推断"),
    ("ADM-A01", "get", "/admin/audit-logs", "Admin", "TECH_OPS,SUPER_ADMIN", None, "audit-log",
     ["page", "pageSize", "actorType", "action", "traceId", "from", "to"], ["E-1901"], "真源"),
]

LIST_RESPONSE_MODELS = {
    "credential-row", "report-summary", "quote-row", "contract", "payment", "notification",
    "usage-hourly-bucket", "audit-log", "sync-task", "channel-binding", "provider-profile",
    "detection-config", "report-template", "review-task", "review-record", "quote-compare",
    "model-info", "detection-result", "quote-item", "compilation-result", "settlement-statement",
    "quote-version", "credential-precheck", "provider-qualification",
}

PAGEABLE = {
    "AUTH-06": False,
}


# --check（只校验）时把所有产物重定向到临时目录，保证校验对仓库**零写副作用**；
# 普通生成模式下 CHECK_OUT 为 None，_out() 即恒等映射。
CHECK_OUT = None


def _out(path: str) -> str:
    if CHECK_OUT is None:
        return path
    return os.path.join(CHECK_OUT, os.path.relpath(path, ROOT))


def write_json(path: str, obj) -> None:
    path = _out(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def schema_file(name: str, body: dict) -> dict:
    # 注意：**不写 $id**。若给 $id 赋 https:// 绝对 URI，模型之间的相对 $ref
    # （如 "model-entry.schema.json"）会被解析成绝对地址去联网拉取，
    # 契约测试直接报 "Failed to load json schema from https://..."。
    # 不写 $id 时基准 URI 就是文件自身位置，相对引用在同目录内正确解析。
    out = {"$schema": "https://json-schema.org/draft/2020-12/schema",
           "title": name}
    out.update(body)
    out.setdefault("type", "object")
    out.setdefault("additionalProperties", True)
    return out


def gen_common() -> None:
    write_json(os.path.join(SCHEMA_DIR, "common", "envelope.schema.json"), schema_file("envelope", {
        "description": "统一响应包体（所有 /api/v1 接口）",
        "required": ["code", "message"],
        "properties": {
            "code": {"type": "string", "enum": ENUMS["ResultCode"]},
            "message": {"type": "string"},
            "data": {},
            "traceId": {"type": "string"},
        },
    }))
    write_json(os.path.join(SCHEMA_DIR, "common", "page.schema.json"), schema_file("page", {
        "description": "分页响应包装：{items,page,pageSize,total}（字段名以 aap-client 读法为准）",
        "required": ["items", "page", "pageSize", "total"],
        "properties": {
            "items": {"type": "array"},
            "page": {"type": "integer", "minimum": 1},
            "pageSize": {"type": "integer", "minimum": 1, "maximum": 200},
            "total": {"type": "integer", "minimum": 0},
        },
    }))
    write_json(os.path.join(SCHEMA_DIR, "common", "error.schema.json"), schema_file("error", {
        "description": "错误响应（code != 0）",
        "required": ["code", "message"],
        "properties": {
            "code": {"type": "string", "enum": [c for c in ENUMS["ResultCode"] if c != "0"]},
            "message": {"type": "string", "minLength": 1},
            "data": {"type": "null"},
            "traceId": {"type": "string"},
            "details": {"type": ["array", "null"], "items": {"type": "object", "properties": {
                "field": STR, "reason": STR}}},
        },
    }))


def gen_models() -> None:
    for name, body in MODELS.items():
        write_json(os.path.join(SCHEMA_DIR, "models", f"{name}.schema.json"), schema_file(name, body))


def gen_requests() -> None:
    for name, body in REQUESTS.items():
        write_json(os.path.join(SCHEMA_DIR, "requests", f"{name}.schema.json"), schema_file(name, body))


def resolve_ref(ref: str) -> str:
    """schema 内部 $ref 是模型文件名，统一改写为可供 openapi 使用的相对路径。"""
    return ref


def deep_rewrite(obj):
    """把 JSON Schema 内部的 $ref 从 'x.schema.json' 改写为 '../models/x.schema.json'（当位于 models 目录内）。"""
    if isinstance(obj, dict):
        return {k: (f"../models/{v}" if k == "$ref" and isinstance(v, str)
                   and not v.startswith(("http", "#", "../", "./")) else deep_rewrite(v))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [deep_rewrite(v) for v in obj]
    return obj


def fix_model_refs() -> None:
    """models/*.schema.json 之间的 $ref 需要相对路径（同目录无需前缀，此处保持同目录引用）。
    requests/*.schema.json 引用 models 需要 ../models/ 前缀。"""
    for name in MODELS:
        p = os.path.join(SCHEMA_DIR, "models", f"{name}.schema.json")
        with open(_out(p), encoding="utf-8") as fh:
            obj = json.load(fh)
        write_json(p, obj)  # 同目录引用保持文件名
    for name in REQUESTS:
        p = os.path.join(SCHEMA_DIR, "requests", f"{name}.schema.json")
        with open(_out(p), encoding="utf-8") as fh:
            obj = json.load(fh)
        write_json(p, deep_rewrite(obj))


def openapi() -> dict:
    components = {}
    for name in MODELS:
        components[_comp(name)] = {"$ref": f"./json-schema/models/{name}.schema.json"}
    for name in REQUESTS:
        components[f"Request{_comp(name)}"] = {"$ref": f"./json-schema/requests/{name}.schema.json"}
    components["Envelope"] = {"$ref": "./json-schema/common/envelope.schema.json"}
    components["PageMeta"] = {"$ref": "./json-schema/common/page.schema.json"}
    components["Error"] = {"$ref": "./json-schema/common/error.schema.json"}
    for k, v in ENUMS.items():
        components[k] = {"type": "string", "enum": v}

    paths: dict[str, dict] = {}
    for (eid, method, path, tag, roles, req, res, params, errors, note) in PATHS:
        op: dict = {
            "operationId": eid,
            "tags": [tag],
            "summary": _summary(eid),
            "description": f"接口 ID `{eid}`（依据：{note}）",
            "x-aap-id": eid,
            "x-aap-source": note,
            "security": [] if roles == "anon" else [{"bearerAuth": []}],
        }
        if roles not in ("anon", "authenticated"):
            op["x-aap-roles"] = roles.split(",")
        p = []
        for q in params:
            p.append({"name": q, "in": "query", "required": False, "schema": _query_schema(q)})
        for ph in [seg.strip("{}") for seg in path.split("/") if seg.startswith("{")]:
            p.append({"name": ph, "in": "path", "required": True, "schema": {"type": "string"}})
        if p:
            op["parameters"] = p
        if req:
            op["requestBody"] = {
                "required": True,
                "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/Request{_comp(req)}"}}},
            }
        op["responses"] = {
            "200": {
                "description": "成功",
                "content": {"application/json": {"schema": _enveloped(res)}},
            }
        }
        if errors:
            op["responses"]["4XX"] = {
                "description": "业务失败：" + ",".join(errors),
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
            }
        paths.setdefault(path, {})[method] = op

    return {
        "openapi": "3.1.0",
        "info": {
            "title": "AAP 云算接入平台 · 服务端 API",
            "version": "1.0.0",
            "description": "供应商端 + 管理端接口。模型定义见 ./json-schema/**；接口清单见 02-API接口模型清单.md。",
        },
        "servers": [{"url": "http://localhost:8084", "description": "本地"}],
        "tags": [{"name": t} for t in ["Auth", "Provider", "Credential", "Detection", "Report", "Quote",
                                       "Contract", "Payment", "Notification", "Usage", "Admin"]],
        "paths": paths,
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
            },
            "schemas": components,
        },
    }


def _comp(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("-"))


def _summary(eid: str) -> str:
    return {
        "AUTH": "账号接入", "PROV": "供应商", "CRED": "凭证", "DET": "检测", "RPT": "报告",
        "QT": "报价", "CON": "合同", "PAY": "打款", "NTF": "站内信", "USE": "用量",
    }.get(eid.split("-")[0], "管理端")


def _query_schema(q: str) -> dict:
    if q in ("page", "pageSize"):
        return {"type": "integer", "minimum": 1}
    return {"type": "string"}


def _enveloped(model: str | None) -> dict:
    if model is None:
        return {"$ref": "#/components/schemas/Envelope"}
    if model in LIST_RESPONSE_MODELS:
        return {
            "allOf": [
                {"$ref": "#/components/schemas/Envelope"},
                {"type": "object", "properties": {"data": {
                    "allOf": [
                        {"$ref": "#/components/schemas/PageMeta"},
                        {"type": "object", "properties": {"items": {"type": "array", "items": {
                            "$ref": f"#/components/schemas/{_comp(model)}"}}}},
                    ]}}},
            ]
        }
    # DET-03 / QT-05 / QT-06 等以 {items:[...]} 返回的接口
    if model in ("detection-result", "quote-item"):
        return {
            "allOf": [
                {"$ref": "#/components/schemas/Envelope"},
                {"type": "object", "properties": {"data": {
                    "oneOf": [
                        {"$ref": f"#/components/schemas/{_comp(model)}"},
                        {"type": "object", "properties": {"items": {"type": "array", "items": {
                            "$ref": f"#/components/schemas/{_comp(model)}"}}}},
                    ]}}},
            ]
        }
    return {
        "allOf": [
            {"$ref": "#/components/schemas/Envelope"},
            {"type": "object", "properties": {"data": {"$ref": f"#/components/schemas/{_comp(model)}"}}},
        ]
    }


def yaml_dump(obj, indent: int = 0) -> str:
    """极简 YAML 输出（仅覆盖本脚本用到的结构：dict/list/str/int/bool/None）。"""
    sp = "  " * indent
    if isinstance(obj, dict):
        if not obj:
            return "{}\n"
        out = []
        for k, v in obj.items():
            key = _yaml_key(k)
            if isinstance(v, (dict, list)) and v:
                out.append(f"{sp}{key}:\n{yaml_dump(v, indent + 1)}")
            elif isinstance(v, (dict, list)):
                out.append(f"{sp}{key}: {'{}' if isinstance(v, dict) else '[]'}\n")
            else:
                out.append(f"{sp}{key}: {_yaml_scalar(v)}\n")
        return "".join(out)
    if isinstance(obj, list):
        out = []
        for item in obj:
            if isinstance(item, dict) and item:
                first = True
                for k, v in item.items():
                    key = _yaml_key(k)
                    prefix = f"{sp}- " if first else f"{sp}  "
                    first = False
                    if isinstance(v, (dict, list)) and v:
                        out.append(f"{prefix}{key}:\n{yaml_dump(v, indent + 2)}")
                    elif isinstance(v, (dict, list)):
                        out.append(f"{prefix}{key}: {'{}' if isinstance(v, dict) else '[]'}\n")
                    else:
                        out.append(f"{prefix}{key}: {_yaml_scalar(v)}\n")
            else:
                out.append(f"{sp}- {_yaml_scalar(item)}\n")
        return "".join(out)
    return f"{sp}{_yaml_scalar(obj)}\n"


def _yaml_key(k: str) -> str:
    return k


def _yaml_scalar(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if s == "":
        return "''"
    if any(ch in s for ch in ":#{}[]&*!|>'\"%@`") or s.strip() != s:
        return json.dumps(s, ensure_ascii=False)
    return s


def emit_endpoint_manifest(out_dir: str) -> int:
    """产出 docs/backend/endpoints.json —— 供「全接口覆盖测试」与定时任务遍历（单一事实源=本脚本 PATHS）。

    任务号（T01…T15）从台账 .agents/state/aap-server-feature-status.csv 反查；台账不存在则该字段为空。
    """
    import csv
    task_of = {}
    ledger = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          ".agents", "state", "aap-server-feature-status.csv")
    if os.path.exists(ledger):
        with open(ledger, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row.get("接口ID"):
                    task_of[row["接口ID"]] = row.get("任务号", "")
    rows = []
    for (eid, method, path, tag, roles, req, res, params, errors, note) in PATHS:
        rows.append({
            "id": eid, "method": method.upper(), "path": "/api/v1" + path, "tag": tag,
            "auth": roles, "request_model": req, "response_model": res,
            "query_params": params, "error_codes": errors, "source": note,
            "task": task_of.get(eid, ""),
        })
    path = _out(os.path.join(out_dir, "endpoints.json"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"total": len(rows), "endpoints": rows}, fh, ensure_ascii=False, indent=2)
    return len(rows)


def artifact_paths() -> list:
    """生成器会写出的**全部**产物路径（--check 必须逐个比对，不能只比 openapi.yaml）。"""
    paths = [os.path.join(SCHEMA_DIR, "common", f"{n}.schema.json") for n in ("envelope", "page", "error")]
    paths += [os.path.join(SCHEMA_DIR, "models", f"{n}.schema.json") for n in MODELS]
    paths += [os.path.join(SCHEMA_DIR, "requests", f"{n}.schema.json") for n in REQUESTS]
    paths += [os.path.join(DOCS, "endpoints.json"), os.path.join(DOCS, "openapi.yaml")]
    return paths


def read_text(path: str):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def main() -> int:
    global CHECK_OUT
    check = "--check" in sys.argv
    paths = artifact_paths()
    tmp = None
    if check:
        import tempfile
        tmp = tempfile.mkdtemp(prefix="aap-gen-check-")
        CHECK_OUT = tmp  # 所有产物改写进临时目录，仓库一个字节都不动
    try:
        gen_common()
        gen_models()
        gen_requests()
        fix_model_refs()
        spec = openapi()
        text = "# 由 tools/gen-backend-models.py 生成，勿手改；改脚本后重跑。\n" + yaml_dump(spec)
        out = os.path.join(DOCS, "openapi.yaml")
        os.makedirs(os.path.dirname(_out(out)), exist_ok=True)
        with open(_out(out), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        manifest = emit_endpoint_manifest(DOCS)
        if check:
            # 全产物比对：先前只比 openapi.yaml，而 gen_* / fix_model_refs / emit_endpoint_manifest
            # 在 check 模式下仍无条件写仓库文件 → schema 与 endpoints.json 的漂移永远检不出来
            # （被静默覆盖），且「只校验」实际改写了 82 个文件。
            drifted = [p for p in paths if read_text(p) != read_text(_out(p))]
            known = {os.path.normcase(os.path.abspath(p)) for p in paths}
            orphans = []
            for root, _dirs, files in os.walk(SCHEMA_DIR):
                for fn in files:
                    if fn.endswith(".schema.json"):
                        fp = os.path.join(root, fn)
                        if os.path.normcase(os.path.abspath(fp)) not in known:
                            orphans.append(fp)  # 生成器已不再产出（模型被删/改名）→ 仓库里的孤儿文件
            if drifted or orphans:
                for p in drifted:
                    print("生成物与生成器不一致: " + os.path.relpath(p, ROOT).replace(os.sep, "/"), file=sys.stderr)
                for p in sorted(orphans):
                    print("孤儿产物（生成器已不产出）: " + os.path.relpath(p, ROOT).replace(os.sep, "/"), file=sys.stderr)
                print(f"check FAILED: 漂移 {len(drifted)} + 孤儿 {len(orphans)} / 共 {len(paths)} 个产物（仓库零写副作用）",
                      file=sys.stderr)
                return 1
            print(f"check ok: {len(paths)}/{len(paths)} 个生成物与生成器完全一致、孤儿 0（只读，仓库未被改写）")
        else:
            print(f"manifest={manifest} endpoints.json written")
        print(f"ok: models={len(MODELS)} requests={len(REQUESTS)} paths={len({t[2] for t in PATHS})} "
              f"operations={len(PATHS)} files={len(MODELS) + len(REQUESTS) + 3}")
        return 0
    finally:
        if tmp is not None:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
            CHECK_OUT = None


if __name__ == "__main__":
    raise SystemExit(main())
