import { chromium } from 'playwright';
const BASE = process.env.BASE;
const b = await chromium.launch(); const p = await (await b.newContext({ viewport: { width: 420, height: 800 } })).newPage();
const errs = []; p.on('pageerror', e => errs.push(e.message));
await p.goto(`${BASE}/v2/library/metrics?q=zzzz`, { waitUntil: 'networkidle' });
console.log('search-empty', await p.getByTestId('search-empty').count() === 1 ? 'ok' : 'FAIL');
await p.getByRole('button', { name: '검색 지우기' }).click(); await p.waitForTimeout(300);
console.log('cleared', await p.locator('a[href*="/library/metrics/"]').count() > 5 ? 'ok' : 'FAIL');
console.log('headline', await p.getByTestId('load-headline').count(), 'flat-note', await p.getByTestId('flat-note').allInnerTexts());
await p.screenshot({ path: 'shots/u7_list.png', fullPage: true });
const href = await p.locator('a[href*="/library/metrics/"]').first().getAttribute('href');
for (const per of ['3m', '1y']) {
  await p.goto(`${BASE}${href}${href.includes('?') ? '&' : '?'}period=${per}`, { waitUntil: 'networkidle' });
  const btn = p.getByRole('button', { name: per === '3m' ? '3개월' : '1년' });
  if (await btn.count()) await btn.first().click();
  await p.waitForTimeout(400);
  console.log(per, 'ticks', (await p.locator('svg').first().locator('xpath=..').innerText()).replace(/\s+/g, ' ').slice(0, 160));
  await p.screenshot({ path: `shots/u7_${per}.png` });
}
console.log('errors', errs.length); await b.close();
