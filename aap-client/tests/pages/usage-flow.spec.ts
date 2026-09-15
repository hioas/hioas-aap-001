/**
 * 序号 22【工作台与我的】我的与用量概览（page-22-2）— 切片 4：交互
 *
 * 交互真源：.calicat/raw/pages/page-22-2/interaction.json =「不存在图层交互数据」
 *   → 交互退 18-API + 设计稿控件语义（台账序号 22 的逐元素分类）：
 *   ① 返回箭头 = navigation（navigateBack；本页由「我的 → 用量与对账」navigateTo 进入，画布无 TabBar）
 *   ② 月份选择 = client-only（原生月份 picker）→ 选中后按新月份重新取数（GET /usage/summary?month=…）
 *   ③ 明细入口「查看逐日 / 逐模型明细」= navigation **无落点**：画布 30 页无明细页、18-API 只有
 *      /usage/hourly 数据接口而无页面 → 不跳转、不弹占位 toast、不臆造路由（台账待拍板）
 */
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import UsagePage from '@/pages/usage/index.vue'
import { getCalls, pushResponse } from '../setup'

const ok = (data: unknown) => ({ statusCode: 200, data: { code: '0', message: 'ok', data } })

const RAW = {
  month: '2024-06',
  request_count: 1_240_000,
  total_tokens: 3_860_000_000,
  amount_total: 12_860,
  mom_saved_amount: 2_140,
  updated_at: '2024-06-14 16:20',
  daily: [
    { stat_date: '2024-06-08', total_tokens: 23_000_000 },
    { stat_date: '2024-06-09', total_tokens: 65_000_000 },
    { stat_date: '2024-06-10', total_tokens: 50_000_000 },
    { stat_date: '2024-06-11', total_tokens: 110_000_000 },
    { stat_date: '2024-06-12', total_tokens: 137_000_000 },
    { stat_date: '2024-06-13', total_tokens: 164_000_000 },
    { stat_date: '2024-06-14', total_tokens: 192_000_000 }
  ],
  models: [
    { model_name: 'gpt-4o-mini', share: 42 },
    { model_name: 'claude-3-5-sonnet', share: 31 },
    { model_name: 'gpt-4o', share: 21 },
    { model_name: '其他', share: 6 }
  ],
  cost: { input: 4_120, output: 8_240, platform_fee: 500, platform_fee_rate: 8, total: 12_860 }
}

async function mountPage() {
  pushResponse(ok(RAW))
  const wrapper = mount(UsagePage)
  await flushPromises()
  return wrapper
}

const req = (index = 0) => getCalls('request')[index].args[0] as Record<string, unknown>
const navUrls = () => getCalls('navigateTo').map((c) => (c.args[0] as Record<string, unknown>).url)

describe('序号 22 · ① 返回箭头 = navigation', () => {
  it('点返回 → uni.navigateBack（画布无 TabBar，本页是 navigateTo 进入的二级页）', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="usage-back"]').trigger('tap')
    await flushPromises()
    expect(getCalls('navigateBack')).toHaveLength(1)
  })
})

describe('序号 22 · ② 月份选择 = client-only + 重新取数', () => {
  it('选中 2024-05 → 第二次请求带 month=2024-05，胶囊更新为响应月份', async () => {
    const wrapper = await mountPage()
    pushResponse(ok({ ...RAW, month: '2024-05', request_count: 900_000 }))
    await wrapper.find('[data-testid="month-picker"]').trigger('change', { detail: { value: '2024-05' } })
    await flushPromises()

    expect(getCalls('request')).toHaveLength(2)
    expect((req(1).data as Record<string, unknown>).month).toBe('2024-05')
    expect(wrapper.find('[data-testid="month-value"]').text()).toBe('2024-05')
    expect(wrapper.find('[data-testid="tile-value"]').text()).not.toBe('1.24M')
  })

  it('非法月份（空串）→ 忽略，不发请求、胶囊不变', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="month-picker"]').trigger('change', { detail: { value: '' } })
    await flushPromises()
    expect(getCalls('request')).toHaveLength(1)
    expect(wrapper.find('[data-testid="month-value"]').text()).toBe('2024-06')
  })

  it('新月份取数失败 → 保留原胶囊月份 + 占位提示，不编造数字', async () => {
    const wrapper = await mountPage()
    pushResponse({ statusCode: 200, data: { code: 'E-3001', message: '用量聚合未完成' } })
    await wrapper.find('[data-testid="month-picker"]').trigger('change', { detail: { value: '2024-05' } })
    await flushPromises()
    expect(wrapper.find('[data-testid="tile-value"]').text()).toBe('—')
    const toast = getCalls('showToast')[0].args[0] as Record<string, unknown>
    expect(toast.title).toBe('数据加载失败，请稍后重试')
  })
})

describe('序号 22 · ③ 明细入口 = navigation 无落点（不臆造路由）', () => {
  it('点「查看逐日 / 逐模型明细」→ 不跳转、不弹占位 toast、不发请求', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="detail-entry"]').trigger('tap')
    await flushPromises()
    expect(navUrls()).toEqual([])
    expect(getCalls('showToast')).toHaveLength(0)
    expect(getCalls('request')).toHaveLength(1)
  })
})
