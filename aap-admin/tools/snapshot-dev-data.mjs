#!/usr/bin/env node
/**
 * 联调数据快照：把本次联调**真实产生**的业务数据落盘保存。
 *
 * 用法：node tools/snapshot-dev-data.mjs [outDir] [phone]
 *   默认 outDir = ../.agents/state/evidence/full-<日期>/data
 *   默认 phone  = 13900000001（超管）
 *
 * 为什么要存：联调结论要有可复核的**数据依据**（哪个报价单、哪份报告、哪笔打款），
 * 而不是只留一句「跑通了」。下次复核或交接时能直接比对。
 *
 * 只读：本工具**只调 GET**，不产生任何副作用。
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const API = process.env.AAP_API || 'http://127.0.0.1:8084/api/v1';
const stamp = new Date().toISOString().slice(0, 10).replace(/-/g, '');
const OUT = process.argv[2] || join('..', '.agents', 'state', 'evidence', `full-${stamp}`, 'data');
const PHONE = process.argv[3] || '13900000001';

mkdirSync(OUT, { recursive: true });

/** RFC3339 UTC（后端 from/to 要求的格式，本地时间直接发会被拒） */
const rfc3339Utc = (d) => d.toISOString().replace(/\.\d{3}Z$/, 'Z');

const post = async (path, body) => {
  const r = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  return r.json();
};
const get = async (path, token) => {
  const r = await fetch(`${API}${path}`, { headers: { Authorization: `Bearer ${token}` } });
  return r.json();
};

const main = async () => {
  // 登录（dev 环境后端回显 dev_code）
  const sms = await post('/auth/sms/send', { phone: PHONE, captcha: 'A7K9' });
  const code = sms?.data?.dev_code;
  if (!code) {
    console.error('拿不到 dev_code（需后端 AAP_SMS_EXPOSE_CODE=true 且不在频控期）：', JSON.stringify(sms).slice(0, 200));
    process.exit(2);
  }
  const login = await post('/auth/sms/login', { phone: PHONE, smsCode: code });
  const token = login?.data?.token;
  if (!token) {
    console.error('登录失败：', JSON.stringify(login).slice(0, 200));
    process.exit(2);
  }
  const me = await get('/auth/me', token);
  console.log(`登录 OK：${me?.data?.phone_masked} role=${me?.data?.role}`);

  // 逐资源拉取（只读）
  const targets = [
    ['providers', '/admin/providers?page=1&pageSize=100'],
    ['reviews-pending', '/admin/reviews?status=PENDING&page=1&pageSize=100'],
    ['reviews-claimed', '/admin/reviews?status=CLAIMED&page=1&pageSize=100'],
    ['contracts', '/admin/contracts?page=1&pageSize=100'],
    ['payments', '/admin/payments?page=1&pageSize=100'],
    ['settlements', '/admin/settlements?page=1&pageSize=100'],
    ['sync-tasks', '/admin/sync/tasks?page=1&pageSize=100'],
    ['channel-bindings', '/admin/channel-bindings?page=1&pageSize=100'],
    // ⚠️ hourly 的 from/to 是**必填**（缺了会 E-1001「from 缺失（RFC3339 UTC）」），
    //    这里取近 30 天，格式用 RFC3339 UTC（本地时间直接发会被拒）。
    [
      'usage-hourly',
      `/admin/usage/hourly?from=${rfc3339Utc(new Date(Date.now() - 30 * 24 * 3600e3))}&to=${rfc3339Utc(new Date())}&page=1&pageSize=500`
    ],
    ['audit-logs', '/admin/audit-logs?page=1&pageSize=50']
  ];

  const summary = {
    capturedAt: new Date().toISOString(),
    api: API,
    loginAs: { phone_masked: me?.data?.phone_masked, role: me?.data?.role, providerId: me?.data?.providerId },
    resources: {}
  };

  for (const [name, path] of targets) {
    try {
      const r = await get(path, token);
      const items = r?.data?.items ?? (Array.isArray(r?.data) ? r.data : []);
      writeFileSync(join(OUT, `${name}.json`), JSON.stringify(r, null, 2), 'utf8');
      summary.resources[name] = {
        code: r?.code,
        total: r?.data?.total ?? (Array.isArray(items) ? items.length : 0),
        file: `${name}.json`,
        error: r?.code && r.code !== '0' ? r.message : undefined
      };
      const flag = r?.code === '0' ? '✓' : '✗';
      console.log(`  ${flag} ${name.padEnd(18)} code=${r?.code} total=${summary.resources[name].total}${r?.message ? ` — ${r.message}` : ''}`);
    } catch (e) {
      summary.resources[name] = { code: 'E-NETWORK', error: e.message };
      console.log(`  ✗ ${name.padEnd(18)} 网络失败：${e.message}`);
    }
  }

  writeFileSync(join(OUT, 'summary.json'), JSON.stringify(summary, null, 2), 'utf8');
  console.log(`\n快照已保存到 ${OUT}`);
  console.log(`汇总：${Object.entries(summary.resources).filter(([, v]) => v.code === '0').length}/${targets.length} 个资源取到`);
};

main().catch((e) => {
  console.error('快照失败:', e.message);
  process.exit(2);
});
