# hioas-aap-001

AAP 新项目骨架（空仓库起步）。当前只包含目录结构与工程约定，**尚无任何实现代码**。

## 目录结构

| 目录 | 角色 | 技术栈（待定） |
|---|---|---|
| `aap-admn` | 管理端 | 待定 |
| `aap-client` | 客户端 | 待定 |
| `aap-server` | 服务端 | 待定 |

> 命名对齐同组织的 `hioas-aap`（aap-admin / aap-h5 / aap-server）。注意本地目录是 `aap-admn`（少一个 `i`），
> 若为笔误，改成 `aap-admin` 后提交即可：
> `git mv aap-admn aap-admin && git commit -m "chore: 修正目录名 aap-admn -> aap-admin"`

## 起步

```bash
git clone git@github.com:hioas/hioas-aap-001.git
cd hioas-aap-001
```

各模块的构建与运行方式在对应目录的 README 中补充。

## 约定

- 默认分支 `main`，改动走 `feat/xxx`、`fix/xxx` 分支 + PR。
- 提交信息：`<type>(<scope>): <描述>`，type 取 `feat|fix|refactor|docs|chore|test|perf`。
- **本仓库为 public**：任何 `.env`、密钥、证书、内网地址一律不得提交。`.gitignore` 已屏蔽常见路径，
  提交前仍建议 `git diff --cached` 自查。
