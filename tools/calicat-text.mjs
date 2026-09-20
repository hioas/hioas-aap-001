#!/usr/bin/env node
/**
 * 抽取 Calicat 设计页的文字节点（按图层顺序）。
 *
 * 用法：node tools/calicat-text.mjs <page-id|design.json 相对路径> [--all]
 *   page-id 形如 page-3-2 → 读 .calicat-admin/raw/pages/<page-id>/design.json
 *
 * 存在的理由：calicat-outline.mjs 的 --text 有深度上限，抽屉类页面的字段容易被截断
 * （曾因此漏看「模型名称」字段，误判原型没这个字段）。本工具全深度遍历、只打文字。
 *
 * ⚠️ 踩过的结构坑：
 *   1. 设计 JSON 顶层是 [{id, layer_data:{...}}]，**真正的节点在 layer_data 里**，
 *      直接读 n.children 会永远拿到空（本工具因此第一版输出为空）。
 *   2. 文本字段是 `content`；文字色是 `fontFill`，`fills` 是背景色。
 */
import fs from 'node:fs'
import path from 'node:path'

const [, , arg, ...flags] = process.argv
if (!arg) {
  console.error('用法: node tools/calicat-text.mjs <page-id|design.json> [--all]')
  process.exit(1)
}
const showStructure = flags.includes('--all')

const file = arg.endsWith('.json')
  ? path.resolve(arg)
  : path.resolve('.calicat-admin/raw/pages', arg, 'design.json')
if (!fs.existsSync(file)) {
  console.error(`找不到设计文件: ${file}`)
  process.exit(1)
}

const root = JSON.parse(fs.readFileSync(file, 'utf8'))
const lines = []

const walk = (n, depth) => {
  // ⚠️ 顶层是**数组** [{id, layer_data}]：先展开数组，否则 n?.layer_data 恒为 undefined，
  //    结果就是「文字节点 0 条」这种静默空输出（本工具第二版踩到的坑）。
  if (Array.isArray(n)) {
    n.forEach((c) => walk(c, depth))
    return
  }
  const L = n?.layer_data ?? n
  if (!L || typeof L !== 'object') return
  const kids = L.children ?? []
  const text = [L.content, L.text, L.characters].find(
    (v) => typeof v === 'string' && v.trim()
  )
  const pad = '  '.repeat(Math.min(depth, 7))
  if (text && !kids.length) {
    lines.push(`${pad}· ${text.trim().replace(/\s+/g, ' ')}`)
  } else if (showStructure && L.name) {
    lines.push(`${pad}[${L.type ?? '?'}] ${L.name}`)
  }
  kids.forEach((c) => walk(c, depth + 1))
}

walk(root, 0)
console.log(`### ${path.basename(path.dirname(file))} — 文字节点 ${lines.length} 条`)
console.log(lines.join('\n'))
