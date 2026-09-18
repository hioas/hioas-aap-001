#!/usr/bin/env node
/**
 * 关闭「本脚本自己的」CDP 浏览器实例 —— 严格归属校验，绝不误伤他人。
 *
 * 用法：node tools/cdp-close-own.mjs <port> [profilePrefix]
 *
 * 归属校验走「端口 → PID → 进程命令行」：
 *   Browser.getBrowserCommandLine 在未加 --enable-automation 的实例上会报
 *   "Command line not returned because --enable-automation not set"，
 *   因此不能用它做唯一依据；读进程命令行对任何实例都成立。
 *
 * 安全规则（多项目共存）：
 *   1) 端口 → LISTENING 的 PID（netstat -ano）；
 *   2) 该 PID 的命令行必须包含本脚本的 profile 前缀（默认 aap-cdp-profile）；
 *   3) 通过 → 先试 CDP Browser.close（优雅），失败再 taskkill /PID（仅此 PID，不按镜像名）；
 *   4) 不通过 → 拒绝并退出码 3（例如 hioas-aim 的 9223 + aim-cdp-profile）。
 */
import { execSync } from 'node:child_process';

const port = process.argv[2] || process.env.AAP_CDP_PORT || '9333';
const prefix = process.argv[3] || 'aap-cdp-profile';

const sh = (cmd) => {
  try {
    return execSync(cmd, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
  } catch {
    return '';
  }
};

function pidOnPort(p) {
  const out = sh('netstat -ano');
  for (const line of out.split(/\r?\n/)) {
    if (!line.includes(`:${p} `) && !line.includes(`:${p}\t`)) continue;
    if (!/LISTENING/i.test(line)) continue;
    const cols = line.trim().split(/\s+/);
    const pid = cols[cols.length - 1];
    if (/^\d+$/.test(pid)) return pid;
  }
  return null;
}

function cmdlineOf(pid) {
  return sh(`powershell -NoProfile -Command "(Get-CimInstance Win32_Process -Filter \\"ProcessId=${pid}\\").CommandLine"`);
}

async function closeViaCdp(p) {
  try {
    const r = await fetch(`http://127.0.0.1:${p}/json/version`, { signal: AbortSignal.timeout(4000) });
    const v = await r.json();
    if (!v.webSocketDebuggerUrl) return false;
    const ws = new WebSocket(v.webSocketDebuggerUrl);
    await new Promise((res, rej) => {
      ws.onopen = res;
      ws.onerror = () => rej(new Error('ws'));
      setTimeout(() => rej(new Error('ws timeout')), 6000);
    });
    ws.send(JSON.stringify({ id: 1, method: 'Browser.close', params: {} }));
    await new Promise((r2) => setTimeout(r2, 1200));
    ws.close();
    return true;
  } catch {
    return false;
  }
}

const pid = pidOnPort(port);
if (!pid) {
  console.log(`端口 ${port} 无 LISTENING 进程（无需关闭）`);
  process.exit(0);
}

const cmdline = cmdlineOf(pid);
const shown = (cmdline.match(/--user-data-dir=("?)([^\s"]+)\1/) || [, , '(未知)'])[2];
const owned = cmdline.toLowerCase().includes(prefix.toLowerCase());

if (!owned) {
  console.error(`拒绝关闭：端口 ${port} 的 PID ${pid} 不属于本脚本（profile 前缀 ${prefix}* 不匹配）`);
  console.error(`  该实例 user-data-dir = ${shown}`);
  console.error('  这可能是其他项目正在使用的浏览器（例如 aim-tdd 的 9223 + aim-cdp-profile）→ 不触碰。');
  process.exit(3);
}

console.log(`归属确认：PID ${pid} / ${shown}`);
const graceful = await closeViaCdp(port);
if (graceful) {
  console.log('已通过 CDP Browser.close 优雅关闭自己的实例（未触碰任何其他浏览器）');
  process.exit(0);
}
console.log('CDP 关闭未生效 → 按精确 PID 关闭自己的实例');
sh(`taskkill /PID ${pid} /T /F`);
console.log(`已关闭 PID ${pid}（仅此进程树，未按镜像名杀进程）`);
process.exit(0);
