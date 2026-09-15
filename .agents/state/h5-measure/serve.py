#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测量/验收用静态服务：托管 dist/build/h5，并把 /api/v1/** 映射为本地 JSON mock。

为什么需要它：h5 构建产物是纯静态目录，用「同名文件」只能 mock 到 /api/v1/credentials 这一层，
而 /api/v1/credentials/{id} 需要 credentials 同时是目录 → 静态文件方案无解。
本脚本按「先目录后文件」查找：/api/v1/credentials → mock/v1/credentials/index，
/api/v1/credentials/c1 → mock/v1/credentials/c1，并统一用 application/json 返回（uni.request 才会解析）。

用法：
  python .agents/state/h5-measure/serve.py <h5根目录> <mock目录> <端口>
  默认：aap-client/dist/build/h5 · .agents/state/h5-measure/api · 5199
非 GET（PUT/POST）一律返回 {"code":"0","message":"ok","data":{}} 并打印方法+路径，便于人工核对调用。
"""
import io
import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join("aap-client", "dist", "build", "h5")
MOCK = sys.argv[2] if len(sys.argv) > 2 else os.path.join(".agents", "state", "h5-measure", "api")
PORT = int(sys.argv[3]) if len(sys.argv) > 3 else 5199


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def log_message(self, fmt, *args):
        sys.stderr.write("[serve] %s\n" % (fmt % args))

    def _mock_file(self, path):
        """把 /api/v1/x/y 映射到 MOCK 下的文件；目录则取 index。"""
        rel = path.split("?", 1)[0].lstrip("/")
        if rel.startswith("api/"):
            rel = rel[4:]
        candidate = os.path.join(MOCK, rel)
        if os.path.isdir(candidate):
            candidate = os.path.join(candidate, "index")
        return candidate if os.path.isfile(candidate) else None

    def _send_json_file(self, filepath):
        with io.open(filepath, "rb") as fh:
            body = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path.startswith("/api/"):
            found = self._mock_file(self.path)
            if found:
                self._send_json_file(found)
                return
            body = json.dumps({"code": "E-2001", "message": "mock 未定义该接口: %s" % path}).encode("utf-8")
            self.send_response(404)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def _ok(self):
        length = int(self.headers.get("Content-Length") or 0)
        payload = self.rfile.read(length).decode("utf-8", "replace") if length else ""
        sys.stderr.write("[serve] %s %s body=%s\n" % (self.command, self.path.split("?", 1)[0], payload[:200]))
        # 写类请求也支持 mock：MOCK/<path>/<method> 或 MOCK/<path>.<method>（method 小写，如 post / put / delete）；
        # 兼容早期只写 post 的 mock（detection-jobs/post）
        rel = self.path.split("?", 1)[0].lstrip("/")
        if rel.startswith("api/"):
            rel = rel[4:]
        method = self.command.lower()
        candidates = [
            os.path.join(MOCK, rel, method),
            os.path.join(MOCK, rel + "." + method),
        ]
        if method != "post":
            candidates.append(os.path.join(MOCK, rel, "post"))
        for candidate in candidates:
            if os.path.isfile(candidate):
                self._send_json_file(candidate)
                return
        body = json.dumps({"code": "0", "message": "ok", "data": {"id": "c1"}}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    do_PUT = _ok
    do_POST = _ok
    do_DELETE = _ok


if __name__ == "__main__":
    sys.stderr.write("[serve] root=%s mock=%s port=%d\n" % (ROOT, MOCK, PORT))
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
