/**
 * 行政区划数据（`src/utils/region-data.ts`）—— 先红后绿
 *
 * 背景（缺陷 7）：档案编辑页原用 `<picker mode="region">`。
 * uni-app H5 **不支持 region**（uni-h5.es.js 里 `REGION: 'region'` 被注释掉，
 * mode 的 validator 直接拒绝）→ H5 上该控件不渲染；微信小程序支持 → **两端不一致**。
 *
 * 口径（用户明确要求）：**同一套源码构建出的 H5 与 mp-weixin 页面必须保持一致**，
 * 不接受 `#ifdef` 分平台两套实现。故改用两端都支持的 `mode="multiSelector"`，
 * 并自带一份行政区划数据（PRD 未定义数据源，记 missing-prd）。
 *
 * 兼容性要求：数据形态必须与微信原生 region picker 的返回**对齐**，
 * 否则老数据（已存的 province/city）回填会错位 —— 尤其**直辖市**在微信里
 * 返回 `['北京市','北京市','朝阳区']`（省 === 市）。
 */
import { describe, expect, it } from 'vitest'
import {
  PROVINCES,
  PROVINCE_NAMES,
  citiesOf,
  provinceIndex,
  cityIndex,
  regionAt,
  DEFAULT_REGION
} from '@/utils/region-data'

describe('行政区划数据 · 结构完整性', () => {
  it('覆盖 34 个省级行政区（23 省 + 5 自治区 + 4 直辖市 + 2 特别行政区）', () => {
    expect(PROVINCES.length).toBe(34)
  })

  it('省名唯一且非空', () => {
    const names = PROVINCES.map((p) => p.name)
    expect(names.every((n) => n && n.trim() === n)).toBe(true)
    expect(new Set(names).size).toBe(names.length)
  })

  it('每个省至少有 1 个市，市名唯一且非空', () => {
    for (const p of PROVINCES) {
      expect(p.cities.length, `${p.name} 没有城市`).toBeGreaterThan(0)
      expect(p.cities.every((c) => c && c.trim() === c), `${p.name} 有空城市名`).toBe(true)
      expect(new Set(p.cities).size, `${p.name} 城市名重复`).toBe(p.cities.length)
    }
  })

  it('直辖市：省 === 市（与微信原生 region picker 返回形态一致）', () => {
    for (const name of ['北京市', '天津市', '上海市', '重庆市']) {
      expect(citiesOf(name)).toEqual([name])
    }
  })
})

describe('行政区划数据 · 查询与回填', () => {
  it('浙江省含杭州市（沿用原默认地区）', () => {
    expect(citiesOf('浙江省')).toContain('杭州市')
  })

  it('广东省含深圳市', () => {
    expect(citiesOf('广东省')).toContain('深圳市')
  })

  it('未知省名返回空数组，不抛异常', () => {
    expect(citiesOf('不存在的省')).toEqual([])
    expect(citiesOf('')).toEqual([])
  })

  it('provinceIndex 与 PROVINCE_NAMES 一致；未知省返回 -1', () => {
    expect(PROVINCE_NAMES[provinceIndex('广东省')]).toBe('广东省')
    expect(provinceIndex('不存在的省')).toBe(-1)
  })

  it('cityIndex 在省内定位；未知市返回 -1', () => {
    expect(citiesOf('广东省')[cityIndex('广东省', '深圳市')]).toBe('深圳市')
    expect(cityIndex('广东省', '不存在的市')).toBe(-1)
    expect(cityIndex('不存在的省', '深圳市')).toBe(-1)
  })

  it('regionAt 按下标取回省市，越界回落首项', () => {
    expect(regionAt(0, 0)).toEqual({ province: PROVINCES[0].name, city: PROVINCES[0].cities[0] })
    const gd = provinceIndex('广东省')
    expect(regionAt(gd, cityIndex('广东省', '深圳市'))).toEqual({ province: '广东省', city: '深圳市' })
    // 越界不得抛（picker 的 columnchange 可能给到已切换列的旧下标）
    expect(regionAt(999, 999).province).toBeTruthy()
  })

  it('默认地区为 浙江省/杭州市（与原实现一致，避免行为漂移）', () => {
    expect(DEFAULT_REGION).toEqual({ province: '浙江省', city: '杭州市' })
  })

  it('省市往返一致：每个省的每个市都能定位回自身', () => {
    for (const p of PROVINCES) {
      const pi = provinceIndex(p.name)
      for (const c of p.cities) {
        const ci = cityIndex(p.name, c)
        expect(ci, `${p.name}/${c} 定位失败`).toBeGreaterThanOrEqual(0)
        expect(regionAt(pi, ci)).toEqual({ province: p.name, city: c })
      }
    }
  })
})
