# 轮次校验装置（**已冻结**：轮次无关，不再逐轮机械派生）

## 为什么有它

历史上每轮巡检的脚本都靠「从上一轮机械派生 + 逐处显式修正」产出（`derive-rNNN.py` / `roll-rNNN.py`）。
那条路线每轮都要重踩「纯数字盲区 / 轮次号写法 / 锚点被整体重写覆盖 / 收尾脚本锚点过期」等一整族缺陷
（技能 `references/pitfalls-round-chain.md` 里 199–251 条几乎全部源于此），实测代价 **每轮 7–9 处返工、6–11 枚提交**，
且产物全部活在 `$TEMP`（系统清理即永久退场，历史 169/177）。

本目录改走**结构性消除**：轮次号由参数给出、纯值由执行器落盘的 `facts` 单一事实源给出，
装置本身进仓库、可重跑、可审计。

## 用法（一条巡检轮 = 三步）

```bash
export PATH="$HOME/bin:$PATH"
cd E:/workspaces/hioas/hioas-aap-001

# ① 两轮全量（HEAD 的独立 worktree 内串行；落盘 facts-<轮次>.log）
bash tools/round-verify/run-round.sh R491

# ② 校验轮分析（facts/raw/coverage → green-verify-<轮次>-*.txt 等 5 条证据；A0a–A23 判据）
python tools/round-verify/analyze.py R491

# ③ 回归面全量复跑（命令表 = manifest.json；4 条证据 + 跨轮比对）
python tools/round-verify/regression.py R491
```

工作目录：`$TEMP/aap-round-verify/<轮次>/`（每轮独立，**不覆盖**历史轮次的证据）。

## 文件

| 文件 | 作用 |
|---|---|
| `manifest.json` | 回归面命令表**单一事实源**（43 审计 + 41 负向自测 = 84 条）。`tag` 是跨轮比对键：**不得改名或删除**（历史 169/177/182） |
| `run-round.sh <ROUND>` | 执行器：并发前置双向对照 → HEAD 独立 worktree → 串行两轮 `mvn -B -ntp test` → 归档 coverage + 测试源 → 回收 → 落盘 facts |
| `analyze.py <ROUND>` | 分析器：A0a–A23（两轮 rc/BUILD SUCCESS/逐类 diff/`@Test` 对账/禁用扫描/覆盖按族相加/窗口与 in-flight 登记）→ `green-verify-*.txt` |
| `regression.py <ROUND>` | 回归面复跑：命令表存在性预检、rc 逐条比对、tag 集合对齐、零写副作用、跨轮 FAIL 归一比对、崩溃通道、**归仓耐久性守卫** |
| `archive-temp-scripts.py` | 归仓：把仍住在 `$TEMP` 的抽查脚本逐字节存档进 `tools/regression/archive/`（`--check` 只读复核 / `--restore` 一键还原） |

## 纪律（踩过的坑，别再犯）

- **绝不可并发跑测试**：`run-round.sh` 自带 jps 前置（正/反双向对照，历史 66/75/241/251），发现别处的测试 JVM 直接 abort。
- 纯值（轮次、窗口起止、HEAD、被测提交、rc）**只从 facts 读**；消费脚本源码里零硬编码（历史 201/206/243-③）。
- 「0 发现 / 0 命中」先怀疑判据：每个解析器都配 `> 0` 正向对照（历史 46/75/98）。
- 证据文件一律 `newline="\n"` 落盘（历史 69/84/146）。
- 多项目共存：不按镜像名杀进程、不 attach 别人的 CDP、只碰自己的 worktree。
