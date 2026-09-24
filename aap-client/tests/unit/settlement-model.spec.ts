/**
 * 供应商端结算单（SET-01 列表 / SET-02 明细）— 视图模型（纯函数）
 *
 * 口径必须与后端 SettlementService 一致（前端不重新推导）：
 *   净额 = 总额 − 平台服务费；状态 DRAFT/CONFIRMED/VOID；周期 = 自然月（UTC）。
 * 这些断言就是「前端口径不许漂移」的护栏：谁改了展示算法，这里先红。
 */
import { describe, expect, it } from 'vitest'
import {
  STATEMENT_STATUS_LABEL,
  money,
  period,
  toSettlementDetail,
  toSettlementLines,
  toSettlementList
} from '@/utils/settlement-model'

describe('settlement-model · 金额与周期', () => {
  it('金额缺值渲染占位「—」，不编造 0（0 会冒充「有数据」）', () => {
    expect(money(null)).toBe('—')
    expect(money(undefined)).toBe('—')
    expect(money('')).toBe('—')
    expect(money(0)).toBe('¥0.00')
    expect(money('61.7')).toBe('¥61.70')
  })

  it('周期展示截到日（后端给 RFC3339 含时区）', () => {
    expect(period('2026-09-01T00:00:00Z', '2026-10-01T00:00:00Z')).toBe('2026-09-01 ~ 2026-10-01')
    expect(period(null, null)).toBe('—')
  })
})

describe('settlement-model · 列表映射', () => {
  it('净额优先取后端 net_amount（与后端同一口径，不在前端重算优先）', () => {
    const rows = toSettlementList({
      items: [
        {
          id: '1',
          statement_no: 'ST2026090001',
          provider_id: '9',
          period_from: '2026-09-01T00:00:00Z',
          period_to: '2026-10-01T00:00:00Z',
          total_amount: 61.7,
          platform_fee: 6.17,
          net_amount: 55.53,
          status: 'CONFIRMED'
        }
      ]
    })
    expect(rows).toHaveLength(1)
    expect(rows[0].no).toBe('ST2026090001')
    expect(rows[0].total).toBe('¥61.70')
    expect(rows[0].fee).toBe('¥6.17')
    expect(rows[0].net).toBe('¥55.53')
    expect(rows[0].statusLabel).toBe('已出账')
    expect(rows[0].tone).toBe('success')
  })

  it('后端未给 net_amount 时按同口径现算（总额 − 平台费）', () => {
    const rows = toSettlementList({
      items: [{ id: '2', total_amount: 100, platform_fee: 10, status: 'DRAFT' }]
    })
    expect(rows[0].net).toBe('¥90.00')
    expect(rows[0].statusLabel).toBe('待平台确认')
    expect(rows[0].tone).toBe('warn')
  })

  it('响应包裹容错：items / list / records / 裸数组都能取到', () => {
    const one = [{ id: '1', status: 'VOID' }]
    expect(toSettlementList({ items: one })).toHaveLength(1)
    expect(toSettlementList({ list: one })).toHaveLength(1)
    expect(toSettlementList({ records: one })).toHaveLength(1)
    expect(toSettlementList(one)).toHaveLength(1)
    expect(toSettlementList(null)).toHaveLength(0)
    expect(toSettlementList({})).toHaveLength(0)
  })

  it('未知状态回落原始码（不静默显示成已知状态）', () => {
    const rows = toSettlementList({ items: [{ id: '3', status: 'PAID_OUT' }] })
    expect(rows[0].statusLabel).toBe('PAID_OUT')
  })

  it('状态字典覆盖后端状态机三态', () => {
    expect(Object.keys(STATEMENT_STATUS_LABEL).sort()).toEqual(['CONFIRMED', 'DRAFT', 'VOID'])
  })
})

describe('settlement-model · 明细与详情', () => {
  it('明细行按 渠道 × 模型 渲染，tokens 千分位', () => {
    const lines = toSettlementLines({
      lines: [
        { id: 'l1', channel_id: '1004', model_name: 'gpt-4o', total_tokens: 72000, amount: 61.7 }
      ]
    })
    expect(lines).toHaveLength(1)
    expect(lines[0].model).toBe('gpt-4o')
    expect(lines[0].channel).toBe('1004')
    expect(lines[0].tokens).toBe('72,000')
    expect(lines[0].amount).toBe('¥61.70')
  })

  it('明细缺 token 时占位，不显示 NaN', () => {
    const lines = toSettlementLines({ lines: [{ id: 'l2', model_name: 'x' }] })
    expect(lines[0].tokens).toBe('—')
    expect(lines[0].channel).toBe('—')
  })

  it('详情带出已关联打款笔数', () => {
    const d = toSettlementDetail({
      id: '5',
      statement_no: 'ST2026090004',
      total_amount: 61.7,
      platform_fee: 6.17,
      status: 'DRAFT',
      payments: [{ id: 'p1' }, { id: 'p2' }]
    })
    expect(d.no).toBe('ST2026090004')
    expect(d.payments).toBe(2)
    expect(d.net).toBe('¥55.53')
  })
})
