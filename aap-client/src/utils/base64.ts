/**
 * ASCII base64（不依赖 btoa / Buffer：小程序与 H5 都能跑）。
 *
 * 序号 22 抽取为公共工具：序号 6 的雷达图与序号 22 的趋势图都要把 SVG 编成 data-URI
 * （mp-weixin 不能渲染内联 <svg>，只能交给 <image>），原先只放在 report-model.ts 里。
 * report-model.ts 仍以同名 re-export 暴露，历史调用方不受影响。
 * SVG 源全部是 ASCII（数值与属性名），因此无需 UTF-8 处理。
 */
export function base64Ascii(input: string): string {
  const table = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
  let out = ''
  for (let i = 0; i < input.length; i += 3) {
    const c1 = input.charCodeAt(i)
    const c2 = i + 1 < input.length ? input.charCodeAt(i + 1) : NaN
    const c3 = i + 2 < input.length ? input.charCodeAt(i + 2) : NaN
    const b1 = c1 >> 2
    const b2 = ((c1 & 3) << 4) | (Number.isNaN(c2) ? 0 : c2 >> 4)
    const b3 = Number.isNaN(c2) ? 64 : ((c2 & 15) << 2) | (Number.isNaN(c3) ? 0 : c3 >> 6)
    const b4 = Number.isNaN(c3) ? 64 : c3 & 63
    out += table[b1] + table[b2] + (b3 === 64 ? '=' : table[b3]) + (b4 === 64 ? '=' : table[b4])
  }
  return out
}
