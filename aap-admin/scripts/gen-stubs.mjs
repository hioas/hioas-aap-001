#!/usr/bin/env node
/**
 * 生成 aap-admin 其余页面的骨架视图。
 *
 * 目的：先让工程能起来、路由能通、外壳能验证，再逐页按 Calicat 设计真源实现。
 * 每个骨架都写明**它对应哪个 Calicat 页码与图层 id**，避免实现时找不到真源。
 */
import { mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = 'src/views';

/** [目录, 标题, 副标题, Calicat 页码, Calicat layer_id, PRD 锚点] */
const PAGES = [
  ['usage', '用量统计', '小时用量 · 供应商对账 · 成本看板', 'page-2', '79568c55-a29f-4365-9b6a-76278a7ce973', 'PRD 13 §9 M12'],
  ['models', '模型管理', '按厂商分组的模型目录', 'page-3', '9b44afa1-dd7f-42af-b9be-f5e696d24a89', 'PRD 13 §10 配置中心'],
  ['providers', '供应商管理', '进件主体与凭证', 'page-4-pc', 'b94a8daa-cdd8-40bc-86b7-1d351b1ff500', 'PRD 13 §2 供应商管理'],
  ['detection', '检测中心', '任务监控 · 报告 · 阈值配置', 'page-5-pc', '5c922560-01d9-42a1-8f5f-e3606ffae587', 'PRD 13 §10 任务监控'],
  ['reviews', '报价审核', '技术指标复核 + 价格审核', 'page-6-pc', 'db837b27-c4e4-4379-a843-f154c84f041c', 'PRD 13 §5 M8'],
  ['contracts', '合同与结算', '合同管理 · 打款记录 · 结算台账', 'page-7-pc', 'bb133713-f2ba-45bb-a543-76d52bc75f06', 'PRD 13 §6 M9'],
  ['compilation', '编译确认台', 'billingexpr 三栏对照与人工确认', '（设计稿未单独出页，见 PRD §7）', '—', 'PRD 13 §7 M10'],
  ['sync', 'new-api 同步', '建渠道 · 写价 · 启停 · 回读', 'page-8-pc-new-api', '5950b19e-1bde-4e88-8705-833e5bd1d51d', 'PRD 13 §8 M11']
];

const tpl = (title, subtitle, pageId, layerId, prd) => `<template>
  <div class="stub">
    <div class="aap-card stub__card">
      <div class="stub__head">
        <span class="stub__title">${title}</span>
        <span class="aap-badge aap-badge--warn">待实现</span>
      </div>
      <p class="stub__sub">${subtitle}</p>
      <el-descriptions :column="1" border size="small" class="stub__src">
        <el-descriptions-item label="设计真源（Calicat）">
          页码 <code>${pageId}</code> · layer_id <code>${layerId}</code>
        </el-descriptions-item>
        <el-descriptions-item label="业务真源（PRD）">${prd}（<code>.calicat/prd/13-管理端PRD.md</code>）</el-descriptions-item>
        <el-descriptions-item label="本地设计数据">
          <code>.calicat-admin/raw/pages/${pageId}/design.json</code>
        </el-descriptions-item>
      </el-descriptions>
      <p class="stub__note">
        本页尚未按设计真源实现。骨架先保证路由/外壳可验证；实现时逐元素对照
        <code>tools/calicat-outline.mjs ${pageId} --all --depth 9</code> 的输出。
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
// 骨架：无逻辑。实现时替换为真实的取数与交互。
</script>

<style scoped>
.stub { display: flex; }
.stub__card { flex: 1; padding: 22px 24px; }
.stub__head { display: flex; align-items: center; gap: 10px; }
.stub__title { font-size: var(--fs-2xl); font-weight: 600; }
.stub__sub { font-size: var(--fs-base); color: var(--c-text-muted); margin: 6px 0 18px; }
.stub__src { margin-bottom: 16px; }
.stub__note { font-size: var(--fs-base); color: var(--c-text-sub); line-height: 1.7; }
code { background: var(--c-surface-alt); padding: 1px 5px; border-radius: var(--r-sm); font-size: var(--fs-sm); }
</style>
`;

let created = 0;
for (const [dir, title, subtitle, pageId, layerId, prd] of PAGES) {
  const target = join(ROOT, dir);
  mkdirSync(target, { recursive: true });
  const file = join(target, 'index.vue');
  if (existsSync(file)) {
    console.log(`skip  ${file}（已存在，不覆盖）`);
    continue;
  }
  writeFileSync(file, tpl(title, subtitle, pageId, layerId, prd), 'utf8');
  console.log(`write ${file}`);
  created++;
}
console.log(`\n新建 ${created} 个骨架视图`);
