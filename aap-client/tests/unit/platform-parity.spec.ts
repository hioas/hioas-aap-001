/**
 * 双端一致性门禁 —— 用户口径：「同一套源码构建出的 h5、mp-weixin 页面应该保持一样！」
 *
 * ## 为什么要有这个门禁
 *
 * 缺陷 7 的教训：`<picker mode="region">` 在 **uni-h5 上不渲染**（uni-h5 源码里
 * `REGION` 被注释掉，`mode` 的 validator 直接拒绝），而微信小程序支持 →
 * 同一套源码，两端页面表现不一致，且**只在 H5 控制台留一条 Vue warn**，很容易漏掉。
 *
 * 光靠人工审计守不住（本次就是人工发现的）。这里把它固化成测试：
 * 任何人再往 src 里写平台分支或用了 H5 不支持的组件属性，`npm test` 直接红。
 *
 * ## 关键设计：不写死白名单，读真实源码
 *
 * 「H5 支持哪些 picker mode」这个事实**从安装的 uni-h5 产物里解析**，
 * 而不是硬编码在测试里 —— 否则 uni-app 升级（比如哪天支持了 region）后，
 * 白名单会变成过期的谎言（假绿）。解析不到 → **直接失败**，绝不放行。
 *
 * ## 例外（唯一）
 *
 * `src/api/base-url.ts` 的接口基址必须分平台（小程序要绝对 URL，H5 走 vite 代理避免 CORS），
 * 但它**不影响页面渲染**。除它之外的运行时平台判断一律视为违规。
 */
import { describe, expect, it } from 'vitest'
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs'
import { join, relative, sep } from 'node:path'

const ROOT = process.cwd()
const SRC = join(ROOT, 'src')
const UNI_H5 = join(ROOT, 'node_modules/@dcloudio/uni-h5/dist/uni-h5.es.js')

/** 允许存在运行时平台判断的文件（白名单要极短，加一条都要有明确理由） */
const PLATFORM_BRANCH_ALLOWLIST = ['src/api/base-url.ts']

/** 递归收集 src 下的源码文件 */
function collect(dir: string, exts: string[]): string[] {
  const out: string[] = []
  for (const name of readdirSync(dir)) {
    const full = join(dir, name)
    if (statSync(full).isDirectory()) out.push(...collect(full, exts))
    else if (exts.some((e) => name.endsWith(e))) out.push(full)
  }
  return out
}

const rel = (p: string) => relative(ROOT, p).split(sep).join('/')

/**
 * 从 uni-h5 产物里解析 Picker 支持的 mode 取值。
 *
 * 源码形态（uni-h5.es.js）：
 *   const mode = {
 *     SELECTOR: "selector",
 *     MULTISELECTOR: "multiSelector",
 *     TIME: "time",
 *     DATE: "date"
 *     // 暂不支持城市选择
 *     // REGION: 'region'      ← 被注释掉 → 解析不到 → 视为不支持
 *   };
 */
function supportedPickerModes(): string[] {
  const src = readFileSync(UNI_H5, 'utf8')
  const block = /const mode = \{([\s\S]*?)\}/.exec(src)
  if (!block) return []
  const modes: string[] = []
  for (const line of block[1].split('\n')) {
    // 只看未被注释的行：注释行以 // 开头
    if (/^\s*\/\//.test(line)) continue
    const m = /:\s*["']([^"']+)["']/.exec(line)
    if (m) modes.push(m[1])
  }
  return modes
}

/** 抓出所有 `<picker ... mode="X" ...>`（含多行属性写法） */
function pickerUsages() {
  const out: { file: string; mode: string }[] = []
  for (const file of collect(SRC, ['.vue'])) {
    const text = readFileSync(file, 'utf8')
    for (const tag of text.match(/<picker\b[\s\S]*?>/g) ?? []) {
      const m = /\bmode\s*=\s*"([^"]*)"/.exec(tag)
      if (m) out.push({ file: rel(file), mode: m[1] })
    }
  }
  return out
}

/** 去掉注释后的文本（仅用于「平台判断」这类**代码**检查，避免注释里的词造成误报） */
function stripComments(text: string): string {
  return text
    .replace(/<!--[\s\S]*?-->/g, ' ') // 模板注释
    .replace(/\/\*[\s\S]*?\*\//g, ' ') // 块注释
    .replace(/\/\/[^\n]*/g, ' ') // 行注释
}

describe('双端一致性门禁 · H5 与 mp-weixin 共用同一套实现', () => {
  it('能解析到 uni-h5 的 Picker mode 表（解析不到就失败，绝不假绿）', () => {
    expect(existsSync(UNI_H5), `未找到 ${rel(UNI_H5)}，无法判定 H5 支持的 mode`).toBe(true)
    const modes = supportedPickerModes()
    expect(modes.length, '解析出的 mode 为空 —— 解析器与 uni-h5 产物结构不匹配了').toBeGreaterThan(0)
    // 这些是当前版本确实支持的；region 明确不支持（源码里被注释）
    expect(modes).toContain('selector')
    expect(modes).toContain('multiSelector')
  })

  it('src 里所有 <picker mode> 都是 H5 也支持的（缺陷 7 的回归护栏）', () => {
    const supported = supportedPickerModes()
    const usages = pickerUsages()
    expect(usages.length, 'src 里一个 picker 都没有？门禁空转了').toBeGreaterThan(0)
    const bad = usages.filter((u) => !supported.includes(u.mode))
    expect(
      bad,
      `以下 picker 用了 H5 不支持的 mode（H5 上控件不渲染，两端不一致）：\n` +
        bad.map((b) => `  ${b.file}: mode="${b.mode}"（H5 支持：${supported.join(' | ')}）`).join('\n')
    ).toEqual([])
  })

  it('region 明确不被 H5 支持（防止 uni-app 升级后本门禁悄悄失效）', () => {
    // 若某天 uni-h5 真支持了 region，这条会红 —— 那是**好事**，
    // 提醒我们重新评估能否用回原生 region；届时改这条并留决策记录。
    expect(supportedPickerModes()).not.toContain('region')
  })

  it('src 里没有条件编译指令（#ifdef / #ifndef / #endif）', () => {
    /**
     * 注意：uni-app 的条件编译指令**本身就是注释**（`// #ifdef MP-WEIXIN`、
     * `<!-- #ifdef MP-WEIXIN -->`、`/* #ifdef ... *\/`），所以不能简单「去注释后搜」。
     * 判据 = 注释标记之后**紧跟**指令关键字；散文里提到 `#ifdef` 不算（否则误报）。
     */
    const directive = /(?:^|\/\/|\/\*|<!--|\*)\s*#(ifdef|ifndef|endif|elif|else)\b/
    const hits: string[] = []
    for (const file of collect(SRC, ['.vue', '.ts', '.js'])) {
      const text = readFileSync(file, 'utf8')
      text.split('\n').forEach((line, i) => {
        if (directive.test(line)) hits.push(`  ${rel(file)}:${i + 1}  ${line.trim()}`)
      })
    }
    expect(hits, `禁止用条件编译分平台给不同 UI，请改用两端都支持的写法：\n${hits.join('\n')}`).toEqual([])
  })

  it('运行时平台判断只允许出现在白名单文件里（注释里的提及不算）', () => {
    const pattern = /uniPlatform|UNI_PLATFORM|process\.env\.UNI_|MP-WEIXIN/
    const offenders: string[] = []
    for (const file of collect(SRC, ['.vue', '.ts'])) {
      const r = rel(file)
      if (PLATFORM_BRANCH_ALLOWLIST.includes(r)) continue
      const text = stripComments(readFileSync(file, 'utf8'))
      text.split('\n').forEach((line, i) => {
        if (pattern.test(line)) offenders.push(`  ${r}:${i + 1}  ${line.trim()}`)
      })
    }
    expect(
      offenders,
      `平台判断只允许在 ${PLATFORM_BRANCH_ALLOWLIST.join(', ')}（接口基址，不影响渲染）。\n` +
        `若确有正当理由，请加进白名单并写明原因：\n${offenders.join('\n')}`
    ).toEqual([])
  })

  it('白名单文件仍存在（防止白名单指向已删除的文件而失去意义）', () => {
    for (const f of PLATFORM_BRANCH_ALLOWLIST) {
      expect(existsSync(join(ROOT, f)), `白名单文件不存在：${f}`).toBe(true)
    }
  })
})
