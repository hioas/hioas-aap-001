# -*- coding: utf-8 -*-
"""把「页面 1 · 品牌区与免责卡结构」用例追加到 tests/pages/login.spec.ts（保持原文件 CRLF 行尾）。

用法: python .agents/state/append-login-structure-tests.py
"""
import io
import os

PATH = os.path.join("aap-client", "tests", "pages", "login.spec.ts")

BLOCK = """
/**
 * 页面 1 · 设计稿结构（page-1-2）
 * 设计：品牌头部 = Logo行[Logo方块 54x54 + spacer 12 + 品牌名块(云算接入 / SUPPLIER ONBOARDING)] + spacer 28 + 定位语块
 *       免责说明 = container(padding 0/16) 里的一张白卡（r16 / padding 16,20 / 描边 #EEF2F7）
 */
describe('页面 1 · 品牌区与免责卡结构按设计稿', () => {
  it('Logo 与品牌名块同处一个 Logo行（不是上下两行）', async () => {
    const wrapper = await mountLogin()
    const row = wrapper.find('.brand__row')
    expect(row.exists(), '缺少 Logo行容器 .brand__row').toBe(true)
    expect(row.find('.brand__logo').exists(), 'Logo方块应在 Logo行内').toBe(true)
    const idBlock = row.find('.brand__id')
    expect(idBlock.exists(), '品牌名块 .brand__id 应在 Logo行内').toBe(true)
    expect(idBlock.find('.brand__name').text()).toBe('云算接入')
    expect(idBlock.find('.brand__en').text()).toBe('SUPPLIER ONBOARDING')
  })

  it('免责说明是 container 内的一张卡片（.disclaimer-wrap > .disclaimer）', async () => {
    const wrapper = await mountLogin()
    const wrap = wrapper.find('.disclaimer-wrap')
    expect(wrap.exists(), '缺少免责说明外层 container .disclaimer-wrap').toBe(true)
    expect(wrap.find('.disclaimer').exists()).toBe(true)
  })
})
"""


def main():
    with io.open(PATH, encoding="utf-8", newline="") as fh:
        text = fh.read()
    if ".brand__row" in text:
        print("已存在，跳过")
        return 0
    eol = "\r\n" if "\r\n" in text else "\n"
    block = BLOCK.replace("\n", eol) if eol == "\r\n" else BLOCK
    with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
        fh.write(text.rstrip("\r\n") + eol + block.lstrip("\n"))
    print("appended -> %s (eol=%r)" % (PATH, eol))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
