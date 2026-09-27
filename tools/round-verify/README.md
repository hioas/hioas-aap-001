# 轮次校验装置（**已冻结**：轮次无关，不再逐轮机械派生）

## 为什么有它

历史上每轮巡检的脚本都靠「从上一轮机械派生 + 逐处显式修正」产出（`derive-rNNN.py` / `roll-rNNN.py`）。
那条路线每轮都要重踩「纯数字盲区 / 轮次号写法 / 锚点被整体重写覆盖 / 收尾脚本锚点过期」等一整族缺陷
（技能 `references/pitfalls-round-chain.md` 里 199–251 条几乎全部源于此），实测代价 **每轮 7–9 处返工、6–11 枚提交**，
且产物全部活在 `$TEMP`（系统清理即永久退场，历史 169/177）。

本目录改走**结构性消除**：轮次号由参数给出、纯值由执行器落盘的 `facts` 单一事实源给出，
装置本身进仓库、可重跑、可审计。

## 用法（一条巡检轮 = 六步）

```bash
export PATH="$HOME/bin:$PATH"
cd E:/workspaces/hioas/hioas-aap-001

# ① 两轮全量（HEAD 的独立 worktree 内串行；落盘 facts-<轮次>.log）
bash tools/round-verify/run-round.sh R491

# ② 校验轮分析（facts/raw/coverage → green-verify-<轮次>-*.txt 等 5 条证据；A0a–A23 判据）
python tools/round-verify/analyze.py R491

# ③ 回归面全量复跑（命令表 = manifest.json；4 条证据 + 跨轮比对）
python tools/round-verify/regression.py R491

# ④ 装置侧证据（装置面改动 + 返工真值 + 交付面零改动三判据；**收尾的前置**：closeout 申报装置侧改动时要求它已存在）
#    注意：该工具**自己落盘**证据文件（`newline="\n"`），stdout 只是状态回显 —— **不要再加 `>` 重定向**，
#    否则重定向会与工具自身的写入争抢同一个文件（实测：文件被回显覆盖，丢失报告标题行，行数 67 → 68）
python tools/round-verify/device-report.py R491 --rework <N> --note <本轮要点.md>

# ⑤ 收尾（写台账行 / coverage-history 行 / 状态文件小节；数字全部由 ①②③ 的证据推出）
python tools/round-verify/closeout.py R491 --rework <N> --note <本轮要点.md> \
       --device-change <改动文件>                  # 申报装置改动：closeout 会**双向**机器核对（申报了必须真有 / 未申报必须真零改动）
       --extra postwrite-check-R491.txt        # ⑥ 才产生的证据必须**先登记**，否则计数少 1
git add <本轮证据 + 台账 + 状态文件 + 工具改动> && git commit   # 主提交

# ⑥ 主提交落地核对（携带文件 / HEAD 树内 / 台账行逐列相等）→ 落盘 postwrite-check-<轮次>.txt
python tools/round-verify/postwrite.py R491 <主提交短号> > .agents/state/evidence/postwrite-check-R491.txt
# ⑦ 台账「提交」列回填主提交短号（独立小提交；写盘前先与 HEAD 逐记录逐列比对，只允许本轮行 c7 一处差异）
python tools/round-verify/backfill-c7.py R491 <主提交短号>
```

顺序纪律：**④ 装置侧证据 → ⑤ 收尾 → ⑥ 主提交核对 → ⑦ 回填**（历史 243-①/219-③：收尾改台账行，
而 ⑥ 的判据是「HEAD 内台账行 ⇔ 工作区行逐列相等」，顺序写反必然响亮失败）；`--extra` 先登记后产出，
避免「证据条数少 1」这类纯数字盲区（历史 201/206）。

收尾更正相位（本轮实测补入）：若**收尾阶段**才发现新的返工（返工真值要改），正确顺序是
**⑦ 回填 c7 → ⑧ `closeout.py --rewrite` 更正描述/状态/history（`--rewrite` 会**保留** c7）→ 独立收尾提交**。
反序（先 `--rewrite` 再回填）会让 `backfill-c7.py` 的前置判据「工作区 ⇔ `HEAD:` 零差异」失败 ——
那不是判据缺陷，而是**顺序**缺陷（历史 243-① 的同族）。

工作目录：`$TEMP/aap-round-verify/<轮次>/`（每轮独立，**不覆盖**历史轮次的证据）。

## 文件

| 文件 | 作用 |
|---|---|
| `manifest.json` | 回归面命令表**单一事实源**（43 审计 + 41 负向自测 = 84 条）。`tag` 是跨轮比对键：**不得改名或删除**（历史 169/177/182） |
| `run-round.sh <ROUND>` | 执行器：并发前置双向对照 → HEAD 独立 worktree → 串行两轮 `mvn -B -ntp test` → 归档 coverage + 测试源 → 回收 → 落盘 facts |
| `analyze.py <ROUND>` | 分析器：A0a–A23（两轮 rc/BUILD SUCCESS/逐类 diff/`@Test` 对账/禁用扫描/覆盖按族相加/窗口与 in-flight 登记）→ `green-verify-*.txt` |
| `regression.py <ROUND>` | 回归面复跑：命令表存在性预检、rc 逐条比对、tag 集合对齐、零写副作用、跨轮 FAIL 归一比对、**崩溃通道的完整理由行集跨轮比对**（`CRASHCHAN tag=… sha256=…`；判据 = 上一轮同处「rc!=0 ∧ FAIL 0 行」的通道理由不得变化，上一轮无该段 ⇒ 判据不可用、**不得判绿**）、**归仓耐久性守卫**（判据 = `sha256` **三方逐字节一致**：索引 ⇔ 归档 ⇔ 原文件，另查索引孤儿与「原文件已丢失」档）。带 `--selftest`（**23** 例判别力实测，纯函数 `durability()`/`crash_reason()`/`crash_diff()` 同源；条数取自该自测的汇总行 `自测：23 PASS / 0 FAIL`，据实更正，勿再写旧口径；**不进 manifest 回归面**，与 `backfill-c7.py --selftest` 同档） |
| `device-report.py <ROUND> --rework N --note <file>` | 装置侧证据（第 ④ 步，**收尾的前置**）：装置面改动（工作区未提交条目 + 逐文件 numstat 走 `git diff HEAD` + `被测提交..HEAD` 提交链）+ 轮次无关性守卫（含判别力对照）+ 交付面零改动三判据 → `device-round-<轮次>.txt` |
| `closeout.py <ROUND> --rework N --note <file>` | 收尾：写台账行 / `coverage-history.txt` 行 / 状态文件小节；数字全部由证据推出，内容级验收（8 列 + 描述逐字符相等 + 锚点 + 幂等）；`--device-change` 双向机器核对装置改动申报（申报了必须真有 / 未申报必须真零改动） |
| `postwrite.py <ROUND> <主提交短号>` | 主提交落地核对：携带文件 / HEAD 树内 / 台账行逐列相等（c7 例外） |
| `backfill-c7.py <ROUND> <主提交短号>` | 台账「提交」列回填（第 ⑦ 步）：写盘前与 `HEAD:` 逐记录逐列比对（只允许本轮行 c7 一处差异，其余差异响亮失败且零副作用），写盘后内容级验收（差异集合 / 记录数 / 物理行数 / 内嵌换行记录数 / CR 五连）+ 短号须是 HEAD 的祖先；`--selftest` = 20 条合成夹具判据（**不进 manifest 回归面**：它是写盘器；条数取自该自测的汇总行 `判据：PASS 20 / FAIL 0`，据实更正，勿再写旧口径）|
| `final-check.py <ROUND> <主提交短号>` | 收尾一致性核对（F0–F18）：描述列 / history 行 / 状态小节 / 装置证据**四处同源**逐组相等 + 自述标记唯一 + 证据文件齐备（带 `--selftest` 合成夹具判别力实测） |
| `archive-temp-scripts.py` | 归仓：把仍住在 `$TEMP` 的抽查脚本逐字节存档进 `tools/regression/archive/`（`--check` 只读复核 / `--restore` 一键还原） |

## 纪律（踩过的坑，别再犯）

- **绝不可并发跑测试**：`run-round.sh` 自带 jps 前置（正/反双向对照，历史 66/75/241/251），发现别处的测试 JVM 直接 abort。
- 归仓守卫判据是**逐字节三方一致**（索引 ⇔ 归档 ⇔ 原文件），不是「归档文件存在」：原文件在归仓后被就地改写时，
  存在性判据照样判绿，而「归档 = 仍在使用的脚本」这个前提已不成立（`--restore` 会还原出过期脚本）；
  改判据时**别忘 `--selftest`** —— 每个分支都要有一条「注入 → 恰好点名该 tag」的判别力实测（历史 46/66/90/94）。
- 纯值（轮次、窗口起止、HEAD、被测提交、rc）**只从 facts 读**；消费脚本源码里零硬编码（历史 201/206/243-③）。
- 「0 发现 / 0 命中」先怀疑判据：每个解析器都配 `> 0` 正向对照（历史 46/75/98）。
- 跨轮比对有三类通道，别只盯前两类：逐条 `rc`、FAIL 明细、**崩溃通道（`rc!=0 ∧ FAIL 0 行`）的理由行集**。
  常驻红通道的 FAIL 明细恒为 0 ⇒ 「rc 没变、理由变了」只有第三类看得见；理由取**完整行集**（不截断、不只取末行，
  本仓实测该理由 4000+ 字符且变化落在中段），并配「旧写法在该注入下判绿」的反证（历史 98/187/218/219）。
- 证据文件一律 `newline="\n"` 落盘（历史 69/84/146）。
- 多项目共存：不按镜像名杀进程、不 attach 别人的 CDP、只碰自己的 worktree。
