#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""回收残留的临时 worktree 目录（装置执行器 `run-round.sh` 的兜底；轮次无关常驻工具）。

为什么需要它（巡检轮真实返工）：**Windows 不允许删除任何进程的当前目录（含其祖先）**。
执行器在 `cd "$WT/aap-server"` 之后跑两轮测试，随后 `git worktree remove --force "$WT"` 会以
`error: failed to delete '<WT>': Permission denied`（rc=255）**半途失败** —— 目录里还剩部分文件、
而 git 已把 worktree 登记项摘除（`git worktree list` 里已无该条）。后果：
`analyze.py` A20 与 `independent.py` J1e/J5g 会响亮 FAIL（「worktree add/remove rc == 0」/「已回收」），
整轮证据不可用。最小复现（本机实测）：在 worktree 的某个子目录里 `cd` 之后执行
`git -C <主库> worktree remove --force <worktree>` ⇒ rc=255 + 目录残留；从树外执行 ⇒ rc=0 + 目录消失。

修法分三层（`run-round.sh`）：① 先 `cd` 出树；② 有界重试（5s×2）；③ 仍残留时由本脚本兜底。
硬约束（防御误用）：**只删路径中含 `aap-round-wt-` 的目录**，其余一律拒绝；
`ignore_errors=True` 后按**实际存在性**给退出码，绝不谎报成功（历史 12/175）。
"""
import os
import shutil
import sys

GUARD = "aap-round-wt-"


def main(argv):
    if len(argv) != 2:
        print("用法: python rm-tree.py <aap-round-wt-* 目录>")
        return 2
    p = argv[1].replace("\\", "/")
    if GUARD not in p:
        print("REFUSE 非临时 worktree 路径（缺 %s）：%s" % (GUARD, p))
        return 3
    if not os.path.isdir(p):
        print("ALREADY_GONE %s" % p)
        return 0
    shutil.rmtree(p, ignore_errors=True)
    gone = not os.path.exists(p)
    print("%s %s" % ("REMOVED" if gone else "RESIDUE", p))
    return 0 if gone else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
