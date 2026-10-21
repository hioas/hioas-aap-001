#!/usr/bin/env python3
"""SDD + TDD 驱动的 agent 任务循环监控器（M1+M2 最小可用实现）。

设计文档：docs/loop/agent-loop-design.md

核心：不问 agent「完成了吗」，只问工作区「事实是否收敛」。
三态：RUNNING（指纹在变）/ DONE（静默+门禁绿）/ STALLED（静默+门禁红+超时）。

DONE 四条件（后两条是反作弊）：
  1. green 命令退出码 0
  2. gate 全部退出码 0
  3. 证据文件 mtime 晚于本 Task 开始时间（防拿历史绿报告冒充）
  4. **任务 watch 范围内**有改动（防"说完成了但没干活"；不按全仓库判 ——
     并发仓库里他方的在制品会白白满足这一条，反作弊就失效了）

用法：
  python tools/loop/loop.py --task T-M4-08
  python tools/loop/loop.py                 # 按 tasks.json 顺序全部
  python tools/loop/loop.py --task T-M4-08 --on-stalled "echo 'continue'"

退出码：0 全部 DONE；3 有 STALLED/ESCALATED；2 配置错误。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

DEFAULT_TASKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.json")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sh(cmd: str, cwd: str, timeout: int = 2400):
    """跑一条命令，返回 (rc, 合并输出, 耗时秒)。"""
    t0 = time.time()
    try:
        # 用 cmd.exe（Maven/Java 是 Windows 程序）：命令须写 cmd 语法，勿用 export 等 bash 内建。
        p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, timeout=timeout)
        out = (p.stdout or b"") + (p.stderr or b"")
        return p.returncode, out.decode("utf-8", "replace"), time.time() - t0
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT after %ss: %s" % (timeout, cmd), time.time() - t0


def git_dirty(repo: str, paths=None):
    """工作区是否有改动。paths 非空时**只看这些路径**（含未跟踪文件）。

    为什么需要 paths：多会话并发写同一仓库时，`git status` 会被他方在制品点亮 —— 那样
    DONE 的第 4 条（"有改动"反作弊）会被别人的改动满足，等于反作弊失效。
    收敛到本任务的 watch 路径后，含义变成"我改的范围里真的有改动"。
    """
    cmd = "git status --porcelain"
    if paths:
        quoted = " ".join('"%s"' % p.replace('"', '\\"') for p in paths)
        cmd += " -- " + quoted
    rc, out, _ = sh(cmd, repo, 120)
    return (rc == 0 and out.strip() != ""), out


def fingerprint(repo: str, watch) -> str:
    """工作区指纹：**被监视路径**的 git 变更 + mtime/size。

    注意 git 部分也要按 watch 收敛：并发仓库里他方的未提交改动会让全仓库 `git status`
    每 tick 都不同 → 指纹永远"在变" → 永远判不出 DONE（实测过这个坑）。
    """
    parts = [git_dirty(repo, watch if watch else None)[1]]
    for rel in watch:
        p = os.path.join(repo, rel)
        if os.path.isfile(p):
            st = os.stat(p)
            parts.append("%s:%d:%d" % (rel, st.st_mtime_ns, st.st_size))
        elif os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in (".git", "node_modules", ".idea")]
                for f in sorted(files):
                    fp = os.path.join(root, f)
                    try:
                        st = os.stat(fp)
                        parts.append("%s:%d:%d" % (os.path.relpath(fp, repo), st.st_mtime_ns, st.st_size))
                    except OSError:
                        pass
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:16]


def run_gate(task, repo: str):
    """跑 green + gate 命令，证据落盘。返回 {key: (rc, evidence_path)}。"""
    ev_dir = os.path.join(repo, task.get("evidence_dir", ".agents/state/evidence"))
    os.makedirs(ev_dir, exist_ok=True)
    results = {}
    commands = []
    if task.get("green"):
        commands.append(("green", task["green"]))
    for i, cmd in enumerate(task.get("gate", [])):
        commands.append(("gate%d" % i, cmd))
    for key, cmd in commands:
        rc, out, secs = sh(cmd, repo)
        path = os.path.join(ev_dir, "%s-%s.txt" % (key, task["id"]))
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# task=%s key=%s rc=%d secs=%.1f at=%s\n" % (task["id"], key, rc, secs, now_iso()))
            fh.write("# cmd=%s\n\n" % cmd)
            fh.write(out)
        results[key] = (rc, path)
        print("    [gate] %-6s rc=%-3d %.1fs -> %s" % (key, rc, secs, os.path.relpath(path, repo)))
    return results


def judge_done(task, results, start_ts: float, repo: str):
    """DONE 四条件。返回 (done, 原因)。"""
    if not results:
        return False, "无门禁结果"
    failed = [k for k, (rc, _) in results.items() if rc != 0]
    if failed:
        return False, "门禁红: %s" % ",".join(failed)
    for key, (_, path) in results.items():
        if os.stat(path).st_mtime < start_ts:
            return False, "证据不新鲜(%s 早于任务开始，疑似历史报告)" % key
    # 第 4 条反作弊：**本任务 watch 范围内**有改动（不是全仓库 —— 并发仓库里他方改动会使该条失效）
    watch = task.get("watch") or []
    dirty, _ = git_dirty(repo, watch if watch else None)
    if not dirty:
        scope = ("（范围：%s）" % ", ".join(watch)) if watch else "（全仓库）"
        return False, "watch 范围内无改动%s —— 说完成但没干活" % scope
    return True, "四条件通过"


def append_ledger(repo: str, entry: dict):
    path = os.path.join(repo, ".agents/loop/ledger.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run_task(task, repo: str, args) -> str:
    tid = task["id"]
    watch = task.get("watch") or ["aap-server/src", "aap-server/src/main/resources/db/migration"]
    print("\n=== %s %s ===" % (tid, task.get("title", "")))
    print("  red : %s" % task.get("red", "(未定义)"))
    print("  green: %s" % task.get("green", "(未定义)"))

    start_ts = time.time()
    last_fp = fingerprint(repo, watch)
    last_change = time.time()
    attempts = 0

    while True:
        fp = fingerprint(repo, watch)
        if fp != last_fp:
            last_fp = fp
            last_change = time.time()
            print("  [%s] RUNNING（工作区在变）" % now_iso())
            time.sleep(args.tick)
            continue

        # 静默：跑门禁判 DONE / STALLED
        results = run_gate(task, repo)
        done, why = judge_done(task, results, start_ts, repo)
        if done:
            print("  [%s] DONE — %s" % (now_iso(), why))
            append_ledger(repo, {"ts": now_iso(), "task": tid, "state": "DONE", "reason": why,
                                 "attempts": attempts, "fingerprint": fp})
            return "DONE"

        idle = time.time() - last_change
        if idle < args.stall_after:
            print("  [%s] RUNNING（静默 %.0fs < 阈值 %ss；门禁未过：%s）" % (now_iso(), idle, args.stall_after, why))
            time.sleep(args.tick)
            continue

        attempts += 1
        print("  [%s] STALLED #%d — %s（静默 %.0fs）" % (now_iso(), attempts, why, idle))
        append_ledger(repo, {"ts": now_iso(), "task": tid, "state": "STALLED", "reason": why,
                             "attempts": attempts, "idle_seconds": int(idle), "fingerprint": fp})
        if attempts >= args.max_attempts:
            print("  [%s] ESCALATED — 超过 %d 次，转人工（不无限重试）" % (now_iso(), args.max_attempts))
            append_ledger(repo, {"ts": now_iso(), "task": tid, "state": "ESCALATED",
                                 "reason": why, "attempts": attempts})
            return "ESCALATED"
        if args.on_stalled:
            rc, out, _ = sh(args.on_stalled, repo)
            print("  [%s] on-stalled rc=%d %s" % (now_iso(), rc, out.strip()[:200]))
        last_change = time.time()  # 给一轮新的观察窗口
        time.sleep(args.tick)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--tasks", default=DEFAULT_TASKS)
    ap.add_argument("--task", default=None, help="只跑指定 task id")
    ap.add_argument("--tick", type=float, default=15.0, help="采样间隔秒")
    ap.add_argument("--stall-after", type=float, default=300.0, help="静默多久判 STALLED")
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--on-stalled", default=None, help="STALLED 时执行的命令（如触发 CLI agent 继续）")
    ap.add_argument("--once", action="store_true", help="只判一次门禁后退出（不自驱等待）")
    args = ap.parse_args()

    repo = os.path.abspath(args.repo)
    with open(args.tasks, encoding="utf-8") as fh:
        doc = json.load(fh)
    tasks = doc["tasks"] if isinstance(doc, dict) else doc
    if args.task:
        tasks = [t for t in tasks if t["id"] == args.task]
        if not tasks:
            print("未找到 task: %s" % args.task, file=sys.stderr)
            return 2

    states = {}
    for task in tasks:
        if args.once:
            start_ts = time.time() - 1
            results = run_gate(task, repo)
            done, why = judge_done(task, results, start_ts, repo)
            print("%s -> %s（%s）" % (task["id"], "DONE" if done else "NOT_DONE", why))
            states[task["id"]] = "DONE" if done else "NOT_DONE"
            continue
        states[task["id"]] = run_task(task, repo, args)

    print("\n=== 汇总 ===")
    for tid, st in states.items():
        print("  %-12s %s" % (tid, st))
    return 0 if all(v == "DONE" for v in states.values()) else 3


if __name__ == "__main__":
    sys.exit(main())
