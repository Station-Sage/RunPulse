// 실서비스 읽기 전용 투어: 페이지 방문·스크린샷·타이밍·링크/버튼 수집·차트 호버 반응 확인.
import { createRequire } from 'module';
import fs from 'fs';
const require = createRequire('/home/ubuntu/projects/RunPulse/scripts/synth_smoke/pw/package.json');
const { chromium } = require('playwright');

const OUT = process.env.OUT;
const SHOTS = OUT + '/screenshots';
const RAW = process.env.RAW; // scratch dir for json/text dumps
const BASE = 'http://localhost:80';
const HDR = { 'CF-Access-Authenticated-User-Email': 'pansongit@gmail.com' };
const pages = JSON.parse(fs.readFileSync(process.env.PAGES, 'utf8')); // [{key, path}]
const VPS = { desktop: { width: 1280, height: 800 }, mobile: { width: 390, height: 844, isMobile: true, hasTouch: true, deviceScaleFactor: 2 } };

const browser = await chromium.launch();
const results = [];
for (const [vpName, vp] of Object.entries(VPS)) {
  for (const pg of pages) {
    // 캐시 없는 첫 방문 측정을 위해 페이지마다 새 컨텍스트
    const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, isMobile: vp.isMobile, hasTouch: vp.hasTouch, deviceScaleFactor: vp.deviceScaleFactor || 1, extraHTTPHeaders: HDR, locale: 'ko-KR' });
    const page = await ctx.newPage();
    const apis = [];
    const errors = [];
    const reqStart = new Map();
    page.on('request', (r) => reqStart.set(r, Date.now()));
    page.on('response', async (r) => {
      const u = r.url();
      const t = Date.now() - (reqStart.get(r.request()) || Date.now());
      if (u.includes('/api/')) {
        let size = 0; try { size = (await r.body()).length; } catch {}
        apis.push({ url: u.replace(BASE, ''), status: r.status(), ms: t, bytes: size });
      }
      if (r.status() >= 400) errors.push(`${r.status()} ${u.replace(BASE, '')}`);
    });
    page.on('pageerror', (e) => errors.push('pageerror ' + e.message));
    page.on('console', (m) => { if (m.type() === 'error') errors.push('console ' + m.text().slice(0, 200)); });
    await page.addInitScript(() => {
      window.__lcp = 0;
      try { new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__lcp = e.startTime; }).observe({ type: 'largest-contentful-paint', buffered: true }); } catch {}
    });
    const t0 = Date.now();
    let status = 0;
    try {
      const resp = await page.goto(BASE + pg.path, { waitUntil: 'load', timeout: 30000 });
      status = resp ? resp.status() : 0;
    } catch (e) { errors.push('goto ' + e.message); }
    const tLoad = Date.now() - t0;
    try { await page.waitForLoadState('networkidle', { timeout: 20000 }); } catch {}
    const tIdle = Date.now() - t0;
    await page.waitForTimeout(400);
    const perf = await page.evaluate(() => {
      const n = performance.getEntriesByType('navigation')[0] || {};
      const fcp = (performance.getEntriesByName('first-contentful-paint')[0] || {}).startTime || 0;
      return { ttfb: Math.round(n.responseStart || 0), domContentLoaded: Math.round(n.domContentLoadedEventEnd || 0), load: Math.round(n.loadEventEnd || 0), fcp: Math.round(fcp), lcp: Math.round(window.__lcp || 0), docH: document.documentElement.scrollHeight, overflowX: document.documentElement.scrollWidth > window.innerWidth + 1 };
    });
    const shot = `${pg.key}-${vpName}.png`;
    try { await page.screenshot({ path: `${SHOTS}/${shot}`, fullPage: true }); } catch (e) { errors.push('shot ' + e.message); }
    let info = {};
    if (vpName === 'desktop') {
      info = await page.evaluate(() => {
        const vis = (el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
        const links = [...document.querySelectorAll('a[href]')].filter(vis).map((a) => ({ text: a.innerText.trim().replace(/\s+/g, ' ').slice(0, 60), href: a.getAttribute('href') }));
        const buttons = [...document.querySelectorAll('button, [role=button], [role=tab], summary, select, input')].filter(vis).map((b) => ({ tag: b.tagName.toLowerCase(), text: (b.innerText || b.value || b.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 60), disabled: !!b.disabled }));
        // 누를 것처럼 보이지만(cursor:pointer 또는 hover 스타일) 링크/버튼이 아닌 요소
        const pseudo = [...document.querySelectorAll('body *')].filter((el) => vis(el) && getComputedStyle(el).cursor === 'pointer' && !el.closest('a,button,[role=button],summary,label,input,select')).slice(0, 30).map((el) => el.tagName.toLowerCase() + ':' + (el.innerText || '').trim().slice(0, 40));
        const svgs = [...document.querySelectorAll('svg')].filter((s) => s.getBoundingClientRect().width > 150 && s.getBoundingClientRect().height > 60).length;
        const text = document.body.innerText;
        return { links, buttons, pseudo, svgs, title: document.title, text };
      });
      fs.writeFileSync(`${RAW}/${pg.key}.txt`, info.text);
      delete info.text;
      // 차트 호버: 큰 SVG 중앙에 마우스를 올려 DOM 텍스트가 바뀌는지(툴팁 여부)
      const chartProbe = [];
      const svgHandles = await page.$$('svg');
      for (const h of svgHandles) {
        const box = await h.boundingBox();
        if (!box || box.width < 150 || box.height < 60) continue;
        if (chartProbe.length >= 8) break;
        try {
          await h.scrollIntoViewIfNeeded();
          const b2 = await h.boundingBox();
          const before = await page.evaluate(() => document.body.innerText.length + '|' + document.querySelectorAll('*').length);
          await page.mouse.move(b2.x + b2.width * 0.6, b2.y + b2.height * 0.5);
          await page.waitForTimeout(250);
          const after = await page.evaluate(() => document.body.innerText.length + '|' + document.querySelectorAll('*').length);
          const tit = await h.evaluate((s) => s.querySelector('title')?.textContent?.slice(0, 60) || s.getAttribute('aria-label') || '');
          chartProbe.push({ w: Math.round(box.width), h: Math.round(box.height), label: tit, hoverChangesDom: before !== after });
        } catch {}
      }
      info.chartProbe = chartProbe;
    }
    results.push({ key: pg.key, path: pg.path, vp: vpName, status, finalUrl: page.url().replace(BASE, ''), tLoad, tIdle, ...perf, apis, errors, shot, ...info });
    console.log(vpName, pg.key, status, 'idle', tIdle, 'ms', 'apis', apis.length, 'err', errors.length);
    await ctx.close();
  }
}
fs.writeFileSync(`${RAW}/tour.json`, JSON.stringify(results, null, 1));
await browser.close();
