# aap-client（供应商报价端 · 小程序 + H5）

uni-app（Vue3 + Vite + TypeScript）实现的供应商端，目标平台**微信小程序**，同一套代码可出 H5 用于可视化验收。

## 快速开始

```bash
npm install
npm test                 # vitest（先红后绿，见 .agents/skills/dev/SKILL.md）
npm run dev:h5           # H5 联调（浏览器）
npm run dev:mp-weixin    # 小程序联调 → 微信开发者工具导入 dist/dev/mp-weixin
npm run build:mp-weixin  # 小程序构建产物 dist/build/mp-weixin
npm run type-check       # vue-tsc --noEmit
```

## 目录

```
src/
├── api/          http.ts（/api/v1 + 统一响应 + 错误码）、auth.ts（账号接入）
├── pages/        login/index.vue（序号 1）、workbench/index.vue（序号 2 占位）
├── styles/       tokens.scss（设计 token 单一来源，取自 Calicat 设计稿）
└── utils/        validators.ts（R-01/R-02/R-48）、cooldown.ts（60s 频控）
tests/
├── unit/         纯逻辑单测（校验、频控、HTTP/接口契约）
└── pages/        页面交互单测（@vue/test-utils + uni.* 打桩，见 tests/setup.ts）
```

## 约定

- **页面顺序与完成定义**：`../docs/aap-client-page-plan.md`、台账 `../.agents/state/aap-feature-status.csv`。
- **接口真相**：`.calicat/prd/18-API设计OpenAPI.md`，路径前缀 `/api/v1`，响应 `{code,message,data}`，错误码见 `17-零歧义执行规格spec.md` §9。
- **设计真相**：`.calicat/raw/pages/<page-id>/design.tree.json`（用 `../.agents/state/design-summary.py` 读）。
- **测试里的 uni API**：`@tap` 用 `trigger('tap')`（不是 click）；`uni.request` 等由 `tests/setup.ts` 打桩，断言用 `getCalls('request'|'showToast'|'navigateTo'|'login')`。
- **视觉验收**：DOM 实测数字优先（见 dev SKILL §4.1），H5 截图存 `../docs/evidence/`。

## 已知待办

- 微信小程序 AppID 未申请，`manifest.json` 里留空；导入开发者工具时选"测试号"。
- 图标：设计稿为矢量图标，当前用 CSS 色块占位（PRD 08 禁用 emoji）。
- sass `legacy-js-api` 告警：待迁移到现代 API。
