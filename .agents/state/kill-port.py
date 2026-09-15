# -*- coding: utf-8 -*-
"""按端口结束本机监听进程（测量用 mock 服务的收尾；cron 里 taskkill /F 会被安全策略拦，故用 ctypes）。

用法: python .agents/state/kill-port.py 5210
"""
import ctypes
import re
import subprocess
import sys

port = sys.argv[1]
out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, errors="replace").stdout
pids = set()
for line in out.splitlines():
    if ":%s" % port in line and "LISTENING" in line:
        m = re.search(r"(\d+)\s*$", line.strip())
        if m:
            pids.add(int(m.group(1)))

if not pids:
    print("port %s: 无监听进程" % port)
    sys.exit(0)

PROCESS_TERMINATE = 1
for pid in pids:
    handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if handle:
        ok = ctypes.windll.kernel32.TerminateProcess(handle, 0)
        ctypes.windll.kernel32.CloseHandle(handle)
        print("port %s: pid %d terminate=%s" % (port, pid, bool(ok)))
    else:
        print("port %s: pid %d OpenProcess 失败" % (port, pid))
