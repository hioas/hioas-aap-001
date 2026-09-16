# -*- coding: utf-8 -*-
"""本轮收尾回写：
1) aap-decisions.md：D2 标记完成 + 追加执行证据（含「src 内 0 命中」口径需修正的拍板请求）
2) aap-tdd-state.md：STATUS / LEASE(free) / 队列 0（D6 挂起）/ 队列 9（换成 D3 等）/ 追加本轮小结后半段
"""
import io
import os
import re

DEC = os.path.join(".agents", "state", "aap-decisions.md")
STATE = os.path.join(".agents", "state", "aap-tdd-state.md")
NL = "\n"

D2_HEAD_OLD = '## D2 · 删除「钱包」入口 —— `待执行`（用户 2026-09-16 明确要求）'
D2_HEAD_NEW = '## D2 · 删除「钱包」入口 —— `已完成 2026-09-16 09:15`（cron 轮 aap-tdd-run-20260916-0835）'

D2_EVIDENCE = """**执行证据（cron 轮 aap-tdd-run-20260916-0835）**

- 代码：`src/pages/workbench/index.vue` 的 `quickEntries` 删掉 `{ label: '钱包', iconBg: '#eff6ff', iconColor: '#2563eb', url: '' }`（只剩 评测/报价/合同/明细），
  并删掉 `onQuick` 里专为它写的 `if (!q.url) { showToast('钱包功能开发中') }` 分支 —— 已无空 `url` 项，分支成了死代码。
  工作台目录内 `grep -n 钱包 src/pages/workbench/index.vue` 只剩 **1 行注释**（写明「按决策 D2 整项删除」，属设计↔决策偏差留痕，见状态文件 §2 第 6 条）。
- 单测（先红后绿）：`tests/pages/workbench.spec.ts` 结构用例「快捷入口 5 个」→「4 个」；「快捷入口跳转」用例改为先断言
  `[data-testid^="quick-"]` 恰为 4 项且 `wrapper.text()` 不含「钱包」；新增「『钱包』入口被删干净（节点不存在 / 文案无钱包 / 无 toast）」。
  红基线：3 failed（2 个新断言 + 结构用例）→ 绿 **16/16**。
- 测量面（430 宽 DOM 实测，两轮独立测量全等）：`__measure-workbench.html` 的 phase2 由「钱包 client-only toast」换成
  「评测 → `/pages/credentials/index`」，并把「钱包」从设计文案清单移入 `removedByDecision`（D2 留痕）。
  复跑结果：`checkFailCount 0/92` · `quickIds=["quick-评测","quick-报价","quick-合同","quick-明细"]` · `walletEntryAbsent=true` ·
  `pageTextHasWallet=false` · `overflowingCount=0` · `navigatedToCredentials=true`；证据 `evidence/review-序号2-{run,actions-run}{1,2}.json`。
- 全量：`npm test` **1145/1145 连跑两轮** · `npm run type-check` exit 0 · `build:mp-weixin` / `build:h5` DONE。
- ⚠️ **验收口径需修正（请拍板）**：D2 原文写的「`src/` 内 `grep -i 钱包` 为 0 命中」按字面**做不到**——
  `src/pages/mine/index.vue`（序号 21「我的页」）、`src/utils/mine-model.ts`、`src/api/payment.ts` 里的「我的钱包」卡
  是**设计稿 page-21-2 的图层**（设计上就有「我的钱包 / 可提现余额 / 提现 / 待结算 / 累计结算」），删掉它才是违背「设计稿优先」。
  建议把该验收改成 **「`src/pages/workbench/**` 内 0 命中」**（当前已满足，仅 1 行偏差留痕注释）；本轮未擅自扩大删除范围。

"""

STATE_QUEUE0 = (
    "0. ~~**目录命名对齐（`git mv aap-client hioas-aap-client`）**~~ —— **挂起，勿再重试**（决策 D6，2026-09-16 前台会话决定："
    "仓库内模块目录沿用 `aap-*` 与 `aap-server`/`aap-admn` 对齐，`hioas-*` 是仓库名约定，不是模块目录约定）。"
    "本轮（08:35 轮）仍在重试前已按旧在办项试过一次，得到 `Permission denied`（用户 dev server 持句柄）→ 自 D6 起**不再重试**。"
)

STATE_QUEUE9_NEW = NL.join(
    [
        "9. **决策台账 `aap-decisions.md` 的待执行项优先于本队列**（前台会话 2026-09-16 建立该文件，状态文件顶部已加提醒）：",
        "   - **D3 · 图例百分比统一且最优**（`待执行`）——最大余数法 + 环形图与图例同分母，是工作台（序号 2）的实质改造，**下轮第一件事**。",
        "   - **D1 的循环侧收尾**：把台账里 `missing-prd` 的接口备注改成「依据 `docs/api/接口字段级schema.md` §x」，"
        "并核对已实现页面字段名与该 schema 是否一致（不一致以 schema 为准改代码）。",
        "   - D2 已由本轮执行完（见 `aap-decisions.md` D2 证据）；D4/D5 的「循环要做的」小改（tokens 顶部注释、"
        "`docs/aap-client-page-plan.md` §4 结论）尚未做。",
        "   - ⚠️ 已向人类提一条拍板：D2 的验收「`src/` 内 grep 钱包 = 0」与设计稿冲突（mine 页的「我的钱包」卡是 page-21-2 图层），建议改为按 `src/pages/workbench/**` 计。",
    ]
)

SUMMARY_PART2 = NL.join(
    [
        "- 2026-09-16 09:15（**同一 cron 轮 `aap-tdd-run-20260916-0835` 的后半段**）· **发现了并发的人类/前台会话决策台账，并执行 D2（删「钱包」入口）**：",
        "  ①**发现**：提交前 `git log` 里出现非本轮的 `cb926a8 docs(api): 补接口字段级 schema + 决策台账 D1-D6（用户拍板）`（08:56:44），"
        "新增 `aap-decisions.md`、`docs/api/接口字段级schema.md`、`push-calicat-doc.py`，并改状态文件顶部加「每轮先读决策台账、待执行决策优先」。"
        "已核对：其状态文件改动仍在（未被本轮覆盖），本轮三个提交**未包含**其任何文件。",
        "  ②**D6**：目录改名**挂起、勿再重试**（`hioas-*` 是仓库名约定）→ 已从队列移除并标注。",
        "  ③**D2 执行（先红后绿）**：工作台快捷入口「钱包」整项删除（连同 `onQuick` 里的 toast 死分支）+ 单测改 4 项断言与「删干净」新用例"
        "（红 3 failed → 绿 16/16）；载体页 phase2 由「钱包 client-only」换成「评测 → 凭证列表」，「钱包」移入 `removedByDecision`；"
        "两轮实测 `checkFailCount 0/92`、`walletEntryAbsent=true`、`pageTextHasWallet=false`、`navigating→/pages/credentials/index`、溢出 0；"
        "全量 `npm test` **1145/1145 ×2**、type-check exit 0、两个 build DONE（证据 `evidence/green-D2-全量轮{1,2}.txt`）。",
        "  ④**向人类提拍板一条**：D2 写的「`src/` 内 grep 钱包 = 0 命中」按字面做不到 —— mine 页的「我的钱包」卡是设计稿 page-21-2 的图层，"
        "删它违背「设计稿优先」；已建议改成按 `src/pages/workbench/**` 计（当前已满足）。本轮未擅自扩大删除范围。",
        "  ⑤**下轮第一件事**：执行 **D3**（图例百分比统一且最优：最大余数法 + 环形图与图例同分母），再回头做队列 8（给序号 3 的载体页补 checks 维度）。",
    ]
)


def main():
    # 1) 决策台账
    with io.open(DEC, encoding="utf-8", newline="") as fh:
        dec = fh.read()
    if "D2 · 删除「钱包」入口 —— `已完成" in dec:
        print("D2 已标记完成，跳过")
    else:
        if D2_HEAD_OLD not in dec:
            raise SystemExit("未找到 D2 标题")
        dec = dec.replace(D2_HEAD_OLD, D2_HEAD_NEW, 1)
        anchor = "## D3 · 图例百分比"
        if anchor not in dec:
            raise SystemExit("未找到 D3 标题")
        dec = dec.replace(anchor, D2_EVIDENCE + anchor, 1)
        with io.open(DEC, "w", encoding="utf-8", newline="") as fh:
            fh.write(dec)
        print("decisions updated")

    # 2) 状态文件
    with io.open(STATE, encoding="utf-8", newline="") as fh:
        st = fh.read()
    lines = st.split(NL)
    lines[0] = re.sub(r"^STATUS:.*$",
                      "STATUS: RUNNING — 报价端小程序 22 页已全部实现（台账待取件 0）。**每轮先读 `aap-decisions.md`**（前台会话 2026-09-16 建立，"
                      "待执行决策优先于本文件在办项）。当前在办：①**D3（图例百分比统一且最优）→ 下轮第一件事** "
                      "②D1 循环侧收尾（台账 missing-prd 备注改成依据 `docs/api/接口字段级schema.md` + 字段名一致性核对）+ D4/D5 的小改 "
                      "③**按序号逐页复核**：22/22 页已有 430 宽载体页，序号 1/2 已带「设计期望值 checks」（checkFails 0/93 与 0/92）；"
                      "3~23 行的 checks 维度待补（队列 8） ④目录改名 **挂起**（D6）。"
                      "本轮另：D2 已执行完（删「钱包」入口）、登录页 auth fixture 缺口已补。历史流水归档在 aap-notes-archive-2026-09-16.md，**不要每轮读**。",
                      lines[0])
    lines[1] = "LEASE: free until -"

    out = []
    hit0 = hit9 = False
    skip_next = False
    for ln in lines:
        if skip_next:
            skip_next = False
            continue
        if ln.startswith("0. **目录命名对齐**"):
            out.append(STATE_QUEUE0)
            hit0 = True
            continue
        if ln.startswith("9. **队列 2"):
            out.append(STATE_QUEUE9_NEW)
            hit9 = True
            skip_next = True  # 该条第二行「（已拍板落点…」一并替换掉
            continue
        out.append(ln)
    if not (hit0 and hit9):
        raise SystemExit("队列 0/9 锚点未命中：hit0=%s hit9=%s" % (hit0, hit9))
    st = NL.join(out)

    anchor = "## 5. 关键命令（照抄可用）"
    if SUMMARY_PART2.split(NL)[0] in st:
        raise SystemExit("小结后半段已存在")
    st = st.replace(anchor, SUMMARY_PART2 + NL + NL + anchor, 1)

    with io.open(STATE, "w", encoding="utf-8", newline="") as fh:
        fh.write(st)
    print("state updated: %d bytes" % len(st.encode("utf-8")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
