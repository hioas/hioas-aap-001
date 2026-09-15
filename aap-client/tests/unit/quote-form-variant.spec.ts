/**
 * 序号 12-v2【报价管理】新增报价单-APIKey 下拉展开（page-apikey）— 视图模型单测（TDD 切片 1，先红）
 *
 * 设计真源：.calicat/raw/pages/page-apikey/design.tree.json（430 宽 · 设计帧 430x1129 · 无 TabBar）
 *   断言里的中文**逐字手抄自设计树**（不引用实现常量做自证）：
 *     前往「我的设置」新建凭证 / 常用 / 沙箱 / 专用
 *     生产环境密钥 / 测试环境密钥 / 数据标注专用
 *     sk-prod-••••••••2f9a · 12 个模型 / sk-test-••••••••7b31 · 8 个模型 / sk-label-••••••••a4c8 · 5 个模型
 *     选择凭证后将自动带出可用模型
 *   与 page-26（12-v1）同页不同帧，本帧差异（不静默统一，写台账）：
 *     · 本帧无步骤卡（内容区只有 基本信息卡 + 模型列表卡）
 *     · 本帧模型空态无底部提示卡，且空态说明为另一句文案；空态说明不套 pt6 包裹层（158 高 vs 164）
 *     · 本帧凭证选择框为展开态（面板贴着选择框下沿，圆角 [12,12,0,0] + [0,0,12,12]）
 * 交互真源：interaction.json =「不存在图层交互数据」→ 交互退 PRD 10/15/17-spec/18-API + 设计稿控件语义
 *   凭证列表 = api(GET /credentials，18-API Credential Tag) · 选中 = api(GET /credentials/{id})
 *   前往「我的设置」新建凭证 = navigation('/pages/settings/index'，画布第 23 页「我的设置」，台账序号 23 未实现)
 */
import { describe, expect, it } from 'vitest'
import {
  CRED_CREATE_ACTION,
  CRED_OPTION_TAG_SANDBOX,
  CRED_OPTION_TAG_SPECIAL,
  CRED_RECOMMENDED,
  CRED_HINT,
  CRED_PLACEHOLDER,
  MODEL_EMPTY_DESC_SHORT,
  SETTINGS_PAGE,
  VARIANT_EXPANDED,
  VARIANT_INITIAL,
  buildCredOptions,
  credSubText,
  modelCountText,
  variantFlags
} from '@/utils/quote-form-model'

describe('序号 12-v2 · 设计稿原文（逐字取自 page-apikey design.tree.json）', () => {
  it('面板底部操作 / 推荐标 / 环境标 / 空态说明 / 目标路由', () => {
    expect(CRED_CREATE_ACTION).toBe('前往「我的设置」新建凭证')
    expect(CRED_RECOMMENDED).toBe('常用')
    expect(CRED_OPTION_TAG_SANDBOX).toBe('沙箱')
    expect(CRED_OPTION_TAG_SPECIAL).toBe('专用')
    expect(MODEL_EMPTY_DESC_SHORT).toBe('选择凭证后将自动带出可用模型')
    expect(SETTINGS_PAGE).toBe('/pages/settings/index')
    expect(CRED_HINT).toBe('选择凭证后，系统将自动带出该凭证下可用的模型列表')
    expect(CRED_PLACEHOLDER).toBe('请选择凭证')
  })
})

describe('序号 12-v2 · variantFlags（同页两帧的差异开关）', () => {
  it('initial 帧（page-26）：面板收起 · 有步骤卡/必填标/单号说明/空态提示卡/填写须知卡 · 空态说明带 pt6', () => {
    expect(variantFlags(VARIANT_INITIAL)).toEqual({
      panelOpen: false,
      showSteps: true,
      showRequired: true,
      showQuoteNoHint: true,
      showEmptyTip: true,
      showNotice: true,
      emptyDescGap: 6,
      credHintGap: 6,
      emptyDesc: '请先在上方选择凭证，系统将自动带出可用模型列表'
    })
  })

  it('expanded 帧（page-apikey）：面板展开 · 且本帧无步骤卡/必填标/单号说明/空态提示卡/填写须知卡', () => {
    expect(variantFlags(VARIANT_EXPANDED)).toEqual({
      panelOpen: true,
      showSteps: false,
      showRequired: false,
      showQuoteNoHint: false,
      showEmptyTip: false,
      showNotice: false,
      emptyDescGap: 0,
      credHintGap: 10,
      emptyDesc: '选择凭证后将自动带出可用模型'
    })
  })
})

describe('序号 12-v2 · 下拉选项视图模型', () => {
  it('模型数文案：设计稿「12 个模型」', () => {
    expect(modelCountText(12)).toBe('12 个模型')
    expect(modelCountText(0)).toBe('0 个模型')
  })

  it('副行 = 脱敏 key · 模型数（设计稿「sk-prod-••••••••2f9a · 12 个模型」）', () => {
    expect(credSubText('sk-prod-••••••••2f9a', '12 个模型')).toBe('sk-prod-••••••••2f9a · 12 个模型')
    expect(credSubText('sk-test-••••••••7b31', '8 个模型')).toBe('sk-test-••••••••7b31 · 8 个模型')
  })

  it('副行缺一半时不编造：只有 key 就只渲染 key，只有模型数就只渲染模型数，都没有则空', () => {
    expect(credSubText('sk-a***5678', '')).toBe('sk-a***5678')
    expect(credSubText('', '3 个模型')).toBe('3 个模型')
    expect(credSubText('', '')).toBe('')
  })

  it('候选项：别名 / 脱敏 key / 模型数 / 环境标 / 推荐标（字段名取 15-数据字典 + 17-spec，缺失不臆造）', () => {
    const opts = buildCredOptions([
      {
        id: 'c1',
        alias: '生产环境密钥',
        api_key_mask: 'sk-prod-••••••••2f9a',
        is_primary: true,
        model_list: new Array(12).fill({ model_name: 'gpt-4o' })
      },
      {
        id: 'c2',
        alias: '测试环境密钥',
        api_key_mask: 'sk-test-••••••••7b31',
        env_tag: '沙箱',
        model_list: new Array(8).fill({})
      }
    ])
    expect(opts).toEqual([
      {
        id: 'c1',
        alias: '生产环境密钥',
        maskText: 'sk-prod-••••••••2f9a',
        subText: 'sk-prod-••••••••2f9a · 12 个模型',
        envTag: '',
        recommended: true
      },
      {
        id: 'c2',
        alias: '测试环境密钥',
        maskText: 'sk-test-••••••••7b31',
        subText: 'sk-test-••••••••7b31 · 8 个模型',
        envTag: '沙箱',
        recommended: false
      }
    ])
  })

  it('17-spec 命名（api_key_masked / is_primary）与 15-数据字典命名（api_key_mask / primary_flag）都认', () => {
    const [a, b] = buildCredOptions([
      { id: 'x', alias: 'X', api_key_masked: 'sk-x***1', primary_flag: true },
      { id: 'y', alias: 'Y', api_key_mask: 'sk-y***2' }
    ])
    expect(a.maskText).toBe('sk-x***1')
    expect(a.subText).toBe('sk-x***1')
    expect(a.recommended).toBe(true)
    expect(b.maskText).toBe('sk-y***2')
    expect(b.recommended).toBe(false)
  })

  it('环境标「沙箱/专用」PRD 零命中 → 服务端不给字段就不渲染（不臆造）', () => {
    const [a] = buildCredOptions([{ id: 'x', alias: 'X', model_list: [] }])
    expect(a.envTag).toBe('')
    expect(a.subText).toBe('0 个模型')
  })

  it('容错：无 id 的项丢弃 · 缺 alias 退化为 id · 空响应 → []', () => {
    expect(buildCredOptions([{ alias: '没有 id' }])).toEqual([])
    const [only] = buildCredOptions([{ id: 'z' }])
    expect(only.alias).toBe('z')
    expect(buildCredOptions(null)).toEqual([])
    expect(buildCredOptions(undefined)).toEqual([])
  })
})
