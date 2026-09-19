import { describe, it, expect } from 'vitest';
import { can, NAV_GROUPS, ROLE_LABEL } from '@/config/nav';
import { CONTRACT_STATUS, PAYMENT_STATUS } from '@/api/admin/contracts';
import { REJECT_REASON_CODES, REVIEW_STATUS } from '@/api/admin/reviews';
import { humanCount, toRfc3339Utc } from '@/api/admin/usage';

describe('aap-admin · 导航与权限（PRD 13 §1/§2）', () => {
  it('导航分组与文案逐字取自设计稿（page-1-pc）', () => {
    expect(NAV_GROUPS.map((g) => g.label)).toEqual(['概览', '进件管理', '下发与同步']);
    const labels = NAV_GROUPS.flatMap((g) => g.items.map((i) => i.label));
    expect(labels).toEqual([
      '状态看板', '用量统计', '模型管理',
      '供应商管理', '检测中心', '报价审核', '合同与结算',
      '编译确认台', 'new-api 同步'
    ]);
  });

  it('角色标签三档（运营商务 / 技术运营 / 超管）', () => {
    expect(ROLE_LABEL.BIZ_OPERATOR).toBe('运营商务');
    expect(ROLE_LABEL.TECH_OPS).toBe('技术运营');
    expect(ROLE_LABEL.SUPER_ADMIN).toBe('超级管理员');
  });

  it('PRD 13 §1 关键权限差异：技术运营**不能**通过报价/写合同/打款', () => {
    expect(can('TECH_OPS', 'quote.approve')).toBe(false);
    expect(can('TECH_OPS', 'contract.write')).toBe(false);
    expect(can('TECH_OPS', 'quote.review')).toBe(true); // 可做技术指标复核
    expect(can('BIZ_OPERATOR', 'quote.approve')).toBe(true);
    expect(can('BIZ_OPERATOR', 'contract.write')).toBe(true);
  });

  it('运营商务**不能**改检测配置 / 读审计日志 / 配 new-api 连接', () => {
    expect(can('BIZ_OPERATOR', 'detection.config')).toBe(false);
    expect(can('BIZ_OPERATOR', 'audit.read')).toBe(false);
    expect(can('BIZ_OPERATOR', 'newapi.config')).toBe(false);
    expect(can('TECH_OPS', 'detection.config')).toBe(true);
    expect(can('TECH_OPS', 'audit.read')).toBe(true);
  });

  it('明文 apikey 只有超管可看（PRD 13 §1）', () => {
    expect(can('BIZ_OPERATOR', 'apikey.reveal')).toBe(false);
    expect(can('TECH_OPS', 'apikey.reveal')).toBe(false);
    expect(can('SUPER_ADMIN', 'apikey.reveal')).toBe(true);
  });

  it('未登记的权限点 = 全员可见（不误伤新菜单）', () => {
    expect(can('BIZ_OPERATOR', 'some.unregistered.action')).toBe(true);
  });
});

describe('aap-admin · 契约对齐后端', () => {
  it('驳回原因码**逐字**等于后端 ReviewService.REASON_CODES（7 个，不自己编）', () => {
    expect(REJECT_REASON_CODES.map((r) => r.code)).toEqual([
      'PRICE_TOO_HIGH', 'PRICE_STRUCTURE_INVALID', 'CACHE_PRICE_MISSING',
      'TECH_RISK', 'VALIDITY_ISSUE', 'MISSING_INFO', 'OTHER'
    ]);
  });

  it('审核状态覆盖后端 REVIEWABLE 两态（PENDING/CLAIMED）+ 终态', () => {
    expect(Object.keys(REVIEW_STATUS)).toEqual(expect.arrayContaining(['PENDING', 'CLAIMED', 'APPROVED', 'REJECTED']));
    expect(REVIEW_STATUS.PENDING.tone).toBe('warn');
    expect(REVIEW_STATUS.CLAIMED.tone).toBe('info');
  });

  it('状态徽章五色映射符合 PRD 13 §3', () => {
    expect(CONTRACT_STATUS.PENDING.tone).toBe('warn'); // 待操作 = 橙
    expect(CONTRACT_STATUS.SIGNED.tone).toBe('success'); // 成功 = 绿
    expect(CONTRACT_STATUS.VOID.tone).toBe('danger'); // 异常 = 红
    expect(CONTRACT_STATUS.ARCHIVED.tone).toBe('muted'); // 终态 = 灰
    expect(PAYMENT_STATUS.PENDING.tone).toBe('warn');
    expect(PAYMENT_STATUS.CONFIRMED.tone).toBe('success');
  });
});

describe('aap-admin · 用量工具函数', () => {
  it('humanCount 用 M/B 口径（与设计稿一致）', () => {
    expect(humanCount(18420000)).toBe('18.42M');
    expect(humanCount(6240000000)).toBe('6.24B');
    expect(humanCount(1500)).toBe('1.50K');
    expect(humanCount(999)).toBe('999');
    expect(humanCount(null)).toBe('—');
  });

  it('toRfc3339Utc 去掉毫秒（后端要求 RFC3339 UTC，本地时间直接发会被拒）', () => {
    const s = toRfc3339Utc(new Date('2026-09-19T10:30:00.123Z'));
    expect(s).toBe('2026-09-19T10:30:00Z');
    expect(s).not.toContain('.');
  });
});
