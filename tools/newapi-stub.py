#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地一体上下游桩（联调用，非交付代码路径）：同时扮演「模型厂商」与「new-api 管理端」。

为什么要合一
------------
一条业务链路的两头在离线环境都没有真身：

* **供应商凭证侧**：预检（CRED-05）与检测引擎（DET）会真实请求
  `GET {base_url}/models`、`POST {base_url}/chat/completions` —— 需要「模型厂商」。
* **M11 同步侧**：上架要真实出站 `POST /api/channel/`（建渠道）、`PUT /api/option/`（写价）、
  `GET /api/channel/{id}`（回读） —— 需要「new-api 管理端」。

两者此前各有一个桩、抢同一个端口（9911），必然二选一。本文件把它们合成一个进程，
一个端口同时提供两套语义，链路才能从「凭证」一路走到「上架」。

角色与鉴权（路径即角色）
------------------------
* `/v1/**`  模型厂商语义（OpenAI 兼容）：只要求带 `Authorization: Bearer <任意>`，
  值不校验 —— 它代表**供应商自己的上游 key**，本来就是任意值。
* `/api/**` new-api 管理端语义：`Authorization: Bearer` 必须等于 `--api-key`，
  只有这样才能复现 401 → `E-1505`（上游拒绝同步请求）这一分支。

用法
----
    python tools/newapi-stub.py --port 9911 --api-key <测试用密钥> \\
        --state "$LOCALAPPDATA/Temp/newapi-stub-state.json"

后端需 `AAP_ALLOW_LOOPBACK=true`（否则 SSRF 守卫会拦环回地址）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOCK = threading.Lock()
STATE = {
    "channels": {},       # id(str) -> channel dict
    "options": {},        # key -> value
    "models": [
        {"id": "gpt-4o", "owned_by": "stub-vendor", "enabled": True},
        {"id": "gpt-4o-mini", "owned_by": "stub-vendor", "enabled": True},
        {"id": "claude-3-5-sonnet", "owned_by": "stub-vendor", "enabled": True},
    ],
    "next_channel_id": 1001,
    "request_log": [],    # 审计：每次调用记 (method, path, body 摘要)
}
STATE_PATH = None
API_KEY = "stub-key"


def load_state(path):
    global STATE
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            for key in STATE:
                if key in loaded:
                    STATE[key] = loaded[key]
        except Exception as exc:  # noqa: BLE001
            print("[stub] 状态文件读取失败，忽略：%s" % exc, file=sys.stderr)


def save_state():
    if not STATE_PATH:
        return
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as fh:
            json.dump(STATE, fh, ensure_ascii=False, indent=2)
    except Exception as exc:  # noqa: BLE001
        print("[stub] 状态文件写入失败：%s" % exc, file=sys.stderr)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # 静音默认日志，改用收尾汇总
        pass

    # ---------------------------------------------------------------- helpers
    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_sse(self, chunks):
        """流式 chat 补全：检测引擎的 TTFT / 流式探测走这里。"""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        for chunk in chunks:
            self.wfile.write(("data: " + json.dumps(chunk, ensure_ascii=False) + "\n\n").encode("utf-8"))
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()
        self.close_connection = True

    def _bearer(self):
        header = self.headers.get("Authorization", "")
        return header[7:].strip() if header.lower().startswith("bearer ") else ""

    def _vendor_ok(self):
        return bool(self._bearer())        # 厂商侧：只要有 key 就算通过（值任意）

    def _admin_ok(self):
        return self._bearer() == API_KEY   # 管理侧：必须是桩的密钥

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:  # noqa: BLE001
            return {"_raw": raw.decode("utf-8", "replace")}

    @staticmethod
    def _query(path_with_query):
        query = {}
        if "?" in path_with_query:
            for part in path_with_query.split("?", 1)[1].split("&"):
                if "=" in part:
                    key, value = part.split("=", 1)
                    query[key] = value
        return query

    @staticmethod
    def _model_id(body):
        model = body.get("model")
        return model if isinstance(model, str) and model else "gpt-4o"

    # ---------------------------------------------------------------- routes
    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]
        query = self._query(self.path)

        if path == "/__health":
            self._send(200, {"status": "ok", "role": "newapi+upstream-stub"})
            return

        # 角色一：模型厂商（OpenAI 兼容）
        if path.endswith("/models"):
            if not self._vendor_ok():
                self._send(401, {"error": {"message": "missing api key", "type": "invalid_request_error"}})
                return
            with LOCK:
                STATE["request_log"].append(["GET", self.path, None])
                data = [{"id": m["id"], "object": "model", "created": 1730000000,
                         "owned_by": m.get("owned_by", "stub-vendor")} for m in STATE["models"]]
            self._send(200, {"object": "list", "data": data})
            return

        # 角色二：new-api 管理端
        with LOCK:
            if not self._admin_ok():
                self._send(401, {"success": False, "message": "unauthorized"})
                return
            STATE["request_log"].append(["GET", self.path, None])
            if path == "/api/models":
                self._send(200, {"success": True, "data": STATE["models"]})
                return
            if path == "/api/channel/":
                self._send(200, {"success": True, "data": list(STATE["channels"].values())})
                return
            if path.startswith("/api/channel/"):
                cid = path.rsplit("/", 1)[-1]
                chan = STATE["channels"].get(str(cid))
                if chan is None:
                    self._send(200, {"success": False, "message": "channel not found"})
                    return
                self._send(200, {"success": True, "data": chan})
                return
            if path == "/api/option/":
                key = query.get("key", "")
                self._send(200, {"success": True, "data": STATE["options"].get(key, "")})
                return
        self._send(404, {"success": False, "message": "not found: " + path})

    def do_POST(self):  # noqa: N802
        path = self.path.split("?")[0]
        body = self._read_json()

        # 角色一：模型厂商（OpenAI 兼容 chat 补全）
        if path.endswith("/chat/completions"):
            if not self._vendor_ok():
                self._send(401, {"error": {"message": "missing api key", "type": "invalid_request_error"}})
                return
            model = self._model_id(body)
            created = int(time.time())
            with LOCK:
                STATE["request_log"].append(["POST", self.path, {"model": model, "stream": bool(body.get("stream"))}])
            if body.get("stream"):
                base = {"id": "chatcmpl-stub", "object": "chat.completion.chunk", "created": created, "model": model}
                chunks = []
                for piece in ("stub", "-", "ok"):
                    delta = dict(base)
                    delta["choices"] = [{"index": 0, "delta": {"content": piece}, "finish_reason": None}]
                    chunks.append(delta)
                tail = dict(base)
                tail["choices"] = [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                chunks.append(tail)
                self._send_sse(chunks)
                return
            self._send(200, {
                "id": "chatcmpl-stub", "object": "chat.completion", "created": created, "model": model,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "stub-ok"},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12},
            })
            return

        # 角色二：new-api 管理端
        with LOCK:
            if not self._admin_ok():
                self._send(401, {"success": False, "message": "unauthorized"})
                return
            STATE["request_log"].append(["POST", self.path, body])
            if path == "/api/channel/":
                cid = STATE["next_channel_id"]
                name = body.get("name") or ("AAP-stub-" + str(cid))
                # 幂等：同名渠道已存在 → 直接返回既有 id（对齐 new-api 语义）
                for existing_id, existing in STATE["channels"].items():
                    if existing.get("name") == name:
                        self._send(200, {"success": True, "message": "duplicated, reuse",
                                         "data": {"id": int(existing_id)}})
                        save_state()
                        return
                STATE["next_channel_id"] = cid + 1
                channel = {
                    "id": cid,
                    "name": name,
                    "key": body.get("key"),
                    "base_url": body.get("base_url"),
                    "models": body.get("models"),
                    "group": body.get("group"),
                    "tag": body.get("tag"),
                    "status": body.get("status", 2),
                    "setting": body.get("setting", {}),
                }
                STATE["channels"][str(cid)] = channel
                save_state()
                self._send(200, {"success": True, "message": "", "data": {"id": cid}})
                return
            if path == "/api/models/sync_upstream":
                save_state()
                self._send(200, {"success": True, "data": len(STATE["models"])})
                return
        self._send(404, {"success": False, "message": "not found: " + path})

    def do_PUT(self):  # noqa: N802
        path = self.path.split("?")[0]
        body = self._read_json()
        with LOCK:
            if not self._admin_ok():
                self._send(401, {"success": False, "message": "unauthorized"})
                return
            STATE["request_log"].append(["PUT", self.path, body])
            if path == "/api/channel/":
                cid = str(body.get("id"))
                chan = STATE["channels"].get(cid)
                if chan is None:
                    self._send(200, {"success": False, "message": "channel not found"})
                    return
                for key, value in body.items():
                    if key != "id":
                        chan[key] = value
                save_state()
                self._send(200, {"success": True, "message": ""})
                return
            if path == "/api/option/":
                key = body.get("key")
                if key:
                    STATE["options"][key] = body.get("value")
                save_state()
                self._send(200, {"success": True, "message": ""})
                return
        self._send(404, {"success": False, "message": "not found: " + path})


def main():
    global STATE_PATH, API_KEY
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9911)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--api-key", default="stub-key")
    parser.add_argument("--state", default="")
    args = parser.parse_args()

    API_KEY = args.api_key
    STATE_PATH = args.state or ""
    load_state(STATE_PATH)

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print("[stub] 一体化上游桩已启动 http://%s:%d（state=%s）" % (args.host, args.port, STATE_PATH or "<内存>"),
          flush=True)
    print("  厂商角色：GET /v1/models · POST /v1/chat/completions", flush=True)
    print("  管理角色：GET|POST /api/channel/ · PUT /api/option/（Bearer 必须等于 --api-key）", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        with LOCK:
            print("[stub] 收尾：渠道 %d 个、option %d 个、请求 %d 次"
                  % (len(STATE["channels"]), len(STATE["options"]), len(STATE["request_log"])),
                  flush=True)
            save_state()


if __name__ == "__main__":
    main()
