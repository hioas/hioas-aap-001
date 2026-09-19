#!/usr/bin/env node
/**
 * 把 Calicat design.json 的图层树摊成可读大纲，供实现页面时逐层对照。
 *
 * 用法：
 *   node tools/calicat-outline.mjs <page-id> [--depth N] [--text] [--all]
 *     --depth N  最大深度（默认 6）
 *     --text     只显示带文本/有意义的节点
 *     --all      显示全部节点（默认会折叠纯容器噪声）
 *
 * 设计数据真源：.calicat-admin/raw/pages/<page-id>/design.json
 * （Calicat 返回的是 [{id, layer_data:{...children}}] 的树）
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const [, , pageId, ...flags] = process.argv;
if (!pageId) {
  console.error('用法: node tools/calicat-outline.mjs <page-id> [--depth N] [--text] [--all]');
  process.exit(2);
}
const maxDepth = (() => {
  const i = flags.indexOf('--depth');
  return i >= 0 ? Number(flags[i + 1]) : 6;
})();
const textOnly = flags.includes('--text');
const showAll = flags.includes('--all');

const file = join('.calicat-admin', 'raw', 'pages', pageId, 'design.json');
const raw = JSON.parse(readFileSync(file, 'utf8'));
const roots = Array.isArray(raw) ? raw.map((n) => n.layer_data ?? n) : [raw];

const num = (v) => (typeof v === 'number' ? Math.round(v) : v);
const brief = (v, n = 46) => {
  const s = String(v ?? '').replace(/\s+/g, ' ').trim();
  return s.length > n ? s.slice(0, n) + '…' : s;
};

let shown = 0;
const walk = (node, depth) => {
  if (!node || depth > maxDepth) return;
  // ⚠️ 文本在 `content`，文字色在 `fontFill`（背景色才是 `fills`）。
  //    最初写成 node.text 导致「文案 0 条」，白排查一轮。
  const content = typeof node.content === 'string' && node.content.trim() ? node.content.trim() : '';
  const isLeafish = !node.children || node.children.length === 0;
  if (showAll || content || isLeafish || depth <= 2) {
    const pad = '  '.repeat(depth);
    const parts = [`${pad}${node.name ?? '(未命名)'}`, `<${node.type}>`];
    if (node.width != null) parts.push(`${num(node.width)}×${num(node.height)}`);
    if (node.x != null) parts.push(`@${num(node.x)},${num(node.y)}`);
    if (node.fills) parts.push(`fill=${brief(typeof node.fills === 'string' ? node.fills : JSON.stringify(node.fills), 26)}`);
    if (node.layout) parts.push(`layout=${node.layout}`);
    if (node.cornerRadius) parts.push(`r=${num(node.cornerRadius)}`);
    if (node.fontSize) parts.push(`fs=${num(node.fontSize)}`);
    if (node.fontWeight) parts.push(`fw=${node.fontWeight}`);
    if (content) parts.push(`"${brief(content, 60)}"${node.fontFamily === 'remixicon' ? ' [icon]' : ''}`);
    if (node.opacity != null && node.opacity !== 1) parts.push(`op=${node.opacity}`);
    console.log(parts.join('  '));
    shown++;
  }
  for (const c of node.children ?? []) walk(c, depth + 1);
};

for (const r of roots) {
  console.log(`### 页面 ${pageId} — ${r.name}  (${num(r.width)}×${num(r.height)})`);
  walk(r, 0);
}
console.log(`\n(共输出 ${shown} 行；--depth ${maxDepth}${textOnly ? ' --text' : ''}${showAll ? ' --all' : ''})`);
