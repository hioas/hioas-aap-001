# -*- coding: utf-8 -*-
"""本轮（aap-tdd-run-20260916-0835）回写状态文件：STATUS / LEASE / 队列 6 / 新增队列 8~9 / 追加本轮小结。

状态文件用 LF 行尾（已实测 grep -c $'\\r' = 0），本脚本一律 LF。
"""
import io
import os

PATH = os.path.join(".agents", "state", "aap-tdd-state.md")
NL = "\n"

NEW_STATUS = (
    "STATUS: RUNNING — 报价端小程序 22 页已全部实现（台账待取件 0）。四条在办："
    "①**目录命名对齐 hioas-aap-client**（用户 dev server 持句柄 → 每轮重试，锁一放就搬）"
    "②**按序号逐页复核**：序号 1/2 本轮补上 430 宽载体页（**22/22 页全覆盖**），并给载体页加了「设计期望值 checks」维度；"
    "已复核页里 3~23 行的 checks 维度**尚未补**（队列 8）"
    "③**序号 9 测量面 fixture 缺口已补并复跑**（历史）"
    "④**登录注册页 auth fixture 缺口本轮已补**（`api/v1/auth/sms/{send,login}/post`，同探针 before/after 见队列 6）。"
    "历史流水归档在 aap-notes-archive-2026-09-16.md，**不要每轮读**。"
)

NEW_LEASE = "LEASE: aap-tdd-run-20260916-0835 until 2026-09-16 09:35"

NEW_ITEM6 = (
    "6. ✅ **给 序号 1（登录注册）、2（工作台）补 430 宽载体页（已完成 2026-09-16 08:58）**："
    "新增 `__measure-login.html`（93 条设计期望值 checks + 6 相交互：空表单 / 缺短信码 / 未勾协议×2 / 获取验证码 / 登录成功；"
    "`?scenario=guard` 只跑校验门）与 `__measure-workbench.html`（92 条 checks + 交互回放 2-actions）；"
    "两页均**两轮独立测量全等**且 `checkFails` 49→0 / 7→0；配套补 `api/v1/auth/sms/{send,login}/post` fixture（红 FAIL 2 → 绿 FAIL 0）；"
    "新增证据维度 `evidence/requests-序号<tag>-run{1,2}.txt`（serve 实收请求行，写请求带 body）——"
    "「校验门有没有偷偷发请求」由 **guard 场景 requests 0 行**直接证明，不再靠页面自报。"
    "（脚本升级：`review-measure.sh` 支持第 5 个参数 url 查询串 + 落 requests 证据；"
    "`check-mock-fixtures.py` 新增两条 POST 检查并把变体目录名（`api-tmp-noauth`）归到基础 mock；"
    "新增 `cmp-flat-phase.py`（扁平老留证 vs 新 phase 跨代对比）、`text-list.py`、`append-login-structure-tests.py`）"
)

NEW_ITEMS = "\n".join(
    [
        "8. **给其余 20 个载体页补「设计期望值 checks」维度**（本轮新立，从序号 3 开始，一页一轮）："
        "现有 3~23 的载体页只测「文案齐、溢出 0、两轮一致」，本轮登录页的经验说明**还能量出与设计树的逐项偏差**"
        "（序号 1 就量出 49 条）。做法照 `__measure-login.html` 的 `chk(k, got, want)`："
        "want 一律取 `.calicat/raw/pages/<page>/design.tree.json` + `node-probe.py` 的声明值，不许凭截图目测。",
        "9. **队列 2「已拍板口径核对」仍未做**：确认 22 页里没有别处把 `/pages/quote-form/index` 当「新建/填写」入口"
        "（已拍板落点 = `/pages/quote-models/index`，page-9）。",
    ]
)

SUMMARY = "\n".join(
    [
        "- 2026-09-16 08:58（cron 轮 `aap-tdd-run-20260916-0835`）· **补 序号 1/2 载体页（队列 6 收官，22/22 页全覆盖）+ 两页按设计树修掉 56 条偏差 + 补 auth fixture（红→绿）**：",
        "  ①**改名**：`git mv aap-client hioas-aap-client` 仍 `Permission denied`（用户 `npm run dev:h5` 持句柄）→ 记一行顺延，**未杀用户进程**（§3.10）。",
        "  ②**新增载体页**（本轮主交付）：`__measure-login.html`（序号 1）与 `__measure-workbench.html`（序号 2），"
        "两页都把设计期望值写进探针：`checkCount` 93 / 92，`checkFailCount` 即「与设计稿的偏差条数」。",
        "  ③**先红后绿**：修前 `checkFailCount` 登录页 **49** / 工作台 **7**（两轮完全一致，逐条清单转录在 "
        "`evidence/red-序号12-修前偏差-转录.txt`）→ 修后 **0 / 0**。登录页按设计重排品牌区为 `Logo行`（Logo 54x54 r16 + 12 + 品牌名块）、"
        "去掉表单卡片 -32px 负边距、输入框 h48/r12/底 rgb(248,250,252)、验证码块与「获取验证码」按钮 112x48 r12 带描边、"
        "勾选框 18x18 r6、免责说明改为 container 内白卡、主/微信按钮 h50 r14；工作台修 7 处色值并让模型序号四行文字逐行给色。",
        "  ④**单测（真红→绿）**：新增 `tests/unit/workbench-model.spec.ts`（序号逐行配色）与 `tests/pages/login.spec.ts` 两个结构用例，"
        "红基线 `evidence/red-序号12-结构用例.txt`（3 failed / 15）→ 绿 15/15；全量 `npm test` **1145/1145 · 70 files 连跑两轮**（evidence/green-序号12-全量轮{1,2}.txt）。",
        "  ⑤**fixture 缺口（同族于序号 9 那次）**：登录页真发的两个 POST 在 mock 里没有 → `check-mock-fixtures.py --mock api-tmp-noauth` FAIL 2 → 补 "
        "`api/v1/auth/sms/{send,login}/post` 后 FAIL 0；**同探针 before/after**：`aap_token` 由 `{\"type\":\"undefined\"}`（等于没写进真 token）"
        "变为 `tk-mock-001` 且跳 `/pages/workbench/index`。",
        "  ⑥**证据有牙齿**：`?scenario=guard`（空表单/缺短信码/未勾协议×2）两轮 serve 实收 **0 行 /api 请求**（requests-序号1-guard-run{1,2}.txt 皆 0 行），"
        "`?scenario=` 全量则实测 `POST /auth/sms/send`（body phone+captcha）→ `POST /auth/sms/login`（body phone+smsCode）→ `GET /provider/profile` + `GET /usage/summary`；"
        "工作台 2-actions 的钱包=client-only（toast「钱包功能开发中」且 hash 不变）、Tab 我的 → `/pages/mine/index`。",
        "  ⑦**跨代对比**：工作台与建页老留证（扁平结构）用新增的 `cmp-flat-phase.py` 对比，公共键 16 → 相同 12，"
        "4 处差异全部 = 老留证那轮 iframe 有可见滚动条（innerWidth 同为 430 而 `docScrollWidth` 415）：docScrollWidth/avatarRight/todoChevronRight 各 +15、"
        "条填 95→102（42% × 轨道宽）→ **非页面漂移**（evidence/cmp-序号2-老留证vs本轮.txt）。",
        "  ⑧**产物与报告**：`build:mp-weixin` exit 0（`dist/build/mp-weixin/pages/{login,workbench}/index.{js,json,wxml,wxss}` 齐备）、"
        "`build:h5` + 430 宽实测、`type-check` exit 0；报告 `evidence/review-measure-20260916-0900.md`（含差异判读 6~9）。",
        "  ⑨**下轮开工第一件事**：改名重试 → 队列 9（已拍板口径核对）→ 队列 8（给序号 3 的载体页补 checks 维度）。",
    ]
)


def main():
    with io.open(PATH, encoding="utf-8", newline="") as fh:
        text = fh.read()
    lines = text.split(NL)
    if not lines[0].startswith("STATUS:"):
        raise SystemExit("首行不是 STATUS")
    lines[0] = NEW_STATUS
    if not lines[1].startswith("LEASE:"):
        raise SystemExit("第二行不是 LEASE")
    lines[1] = NEW_LEASE
    text = NL.join(lines)

    out = []
    hit6 = hit7 = False
    for ln in text.split(NL):
        if ln.startswith("6. **给 序号 1（登录注册）、2（工作台）补 430 宽载体页**"):
            out.append(NEW_ITEM6)
            hit6 = True
            continue
        if ln.startswith("7. （工具卫生）"):
            out.append(ln)
            out.append(NEW_ITEMS)
            hit7 = True
            continue
        out.append(ln)
    if not (hit6 and hit7):
        raise SystemExit("队列 6/7 锚点未命中：hit6=%s hit7=%s" % (hit6, hit7))
    text = NL.join(out)

    anchor = "## 5. 关键命令（照抄可用）"
    if SUMMARY.split(NL)[0] in text:
        raise SystemExit("小结已存在")
    text = text.replace(anchor, SUMMARY + NL + NL + anchor, 1)

    with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("state updated: %d bytes" % len(text.encode("utf-8")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
