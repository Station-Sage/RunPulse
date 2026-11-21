// 실데이터 사본 대상 API 응답 p95 + 모바일 LCP/CLS 측정
import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:8791';
const PAGES = ['today', 'library', 'library/activities', 'library/metrics', 'coach', 'coach/plan'];
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }).catch(() => chromium.launch());
const pct = (a, q) => { const s = [...a].sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.ceil(q * s.length) - 1)]; };

const ctx0 = await b.newContext();
const pg = await ctx0.newPage();
const urls = new Set();
pg.on('request', (r) => { const u = new URL(r.url()); if (u.pathname.startsWith('/api/')) urls.add(u.pathname + u.search); });
for (const p of PAGES) { await pg.goto(`${BASE}/v2/${p}`); await pg.waitForLoadState('networkidle'); }
const list = [...urls].filter((u) => !/stream|messages|events/.test(u)).slice(0, 25);
console.log('endpoints', list.length);
const rows = [];
for (const u of list) {
  const t = [];
  let bad = 0;
  for (let i = 0; i < 15; i++) {
    const s = Date.now();
    const r = await ctx0.request.get(BASE + u);
    t.push(Date.now() - s);
    if (r.status() >= 500) bad++;
  }
  rows.push([u.slice(0, 70), pct(t, 0.5), pct(t, 0.95), bad]);
}
rows.sort((a, b2) => b2[2] - a[2]);
for (const r of rows) console.log(`${String(r[2]).padStart(5)}ms p95 | ${String(r[1]).padStart(4)}ms p50 | 5xx ${r[3]} | ${r[0]}`);
await ctx0.close();

const ctx = await b.newContext({ viewport: { width: 360, height: 720 }, deviceScaleFactor: 2, isMobile: true });
for (const p of PAGES) {
  const pa = await ctx.newPage();
  await pa.addInitScript(() => {
    window.__cwv = { lcp: 0, cls: 0 };
    new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__cwv.lcp = e.startTime; }).observe({ type: 'largest-contentful-paint', buffered: true });
    new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cwv.cls += e.value; }).observe({ type: 'layout-shift', buffered: true });
  });
  const cdp = await ctx.newCDPSession(pa);
  await cdp.send('Network.enable');
  await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 150, downloadThroughput: 200 * 1024, uploadThroughput: 200 * 1024 });
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
  await pa.goto(`${BASE}/v2/${p}`);
  await pa.waitForLoadState('networkidle');
  await pa.waitForTimeout(1500);
  const v = await pa.evaluate(() => window.__cwv);
  console.log(`CWV ${p.padEnd(20)} LCP ${Math.round(v.lcp)}ms CLS ${v.cls.toFixed(3)}`);
  await pa.close();
}
await b.close();
