#!/usr/bin/env node
/**
 * 门禁：CSS 注释里不得出现「星号紧跟斜杠」序列（会提前终止注释）。
 *
 * 为什么需要：tokens.css 的文件头注释里写了路径 `pages/[星]/design.json`，
 * 其中那两个字符合起来被 CSS 解析器当作**注释结束符**，导致紧随其后的 `:root {...}`
 * 整块被丢弃 —— **全部设计令牌消失、页面完全没有样式**，而构建、类型检查、
 * 接口调用全部照常通过（问题只在 CSS 解析层，其它门禁都看不见）。
 *
 * 判据（两类都查）：
 *   1. 单行内出现「星号紧跟斜杠」，且其后还有非空白内容（= 提前终止）
 *   2. 注释块内部再出现结束符
 *
 * 用法：node tools/check-css-comments.mjs   （非 0 退出 = 有问题）
 *
 * 自嘲一句：本文件第一版就踩了同一个坑 —— 头注释里引用了「注释块开闭符号」的写法，
 * 结果把自己注释提前终止了。写这类「检测某序列」的工具时，**不许在注释里复现该序列**。
 */
import { readFileSync, globSync } from 'node:fs';

const files = [...globSync('src/**/*.css'), ...globSync('src/**/*.vue'), ...globSync('src/**/*.ts')];
const problems = [];

for (const f of files) {
  const txt = readFileSync(f, 'utf8');
  const lines = txt.split(/\r?\n/);

  // 1) 逐行找「注释行里出现 星号+斜杠」
  lines.forEach((line, i) => {
    const s = line.trim();
    if (!s.startsWith('*') && !s.startsWith('/*')) return;
    const body = s.startsWith('/*') ? s.slice(2) : s.slice(1);
    const at = body.indexOf('*/');
    // 正常结尾是行末的 */；出现在中间就是提前终止
    if (at >= 0 && body.slice(at + 2).trim() !== '') {
      problems.push({ f, line: i + 1, why: '注释行中间出现 */（提前终止）', text: s.slice(0, 90) });
    }
  });

  // 2) 块级：/* ... */ 内部再出现 */
  let from = 0;
  for (;;) {
    const open = txt.indexOf('/*', from);
    if (open < 0) break;
    const close = txt.indexOf('*/', open + 2);
    if (close < 0) break;
    const inner = txt.slice(open + 2, close);
    const again = inner.indexOf('*/');
    if (again >= 0) {
      const lineNo = txt.slice(0, open + 2 + again).split(/\r?\n/).length;
      problems.push({ f, line: lineNo, why: '注释块内部再出现 */', text: inner.slice(Math.max(0, again - 30), again + 20) });
    }
    from = close + 2;
  }
}

if (problems.length) {
  console.error(`✗ CSS 注释提前终止 ${problems.length} 处（会导致其后规则整块丢失）：\n`);
  for (const p of problems) console.error(`  ${p.f}:${p.line}  ${p.why}\n      ${p.text}`);
  console.error('\n修法：把注释里的 `星号+斜杠` 改写掉，例如把路径写成 pages/[星]/design.json 的替代描述。');
  process.exit(1);
}
console.log(`✓ CSS 注释检查通过（扫描 ${files.length} 个文件，无提前终止）`);
