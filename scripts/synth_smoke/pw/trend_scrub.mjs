// 메트릭 상세 추세 차트 스크럽 판독 + 스크린샷(shots/trend_scrub.png). 환경: BASE, SLUG(기본 ctl)
import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:18099';
const b = await chromium.launch();
const page = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
await page.goto(`${BASE}/v2/library/metrics/${process.env.SLUG || 'ctl'}`, { waitUntil: 'networkidle' });
const chart = page.locator('[role=slider][aria-label*="눌러서"]');
const box = await chart.boundingBox();
const readout = () => chart.locator('xpath=preceding-sibling::div[1]').innerText();
console.log('default:', (await readout()).replace(/\n+/g, ' '));
await page.mouse.move(box.x + box.width * 0.5, box.y + 40);
await page.waitForTimeout(150);
console.log('mid:', (await readout()).replace(/\n+/g, ' '));
await page.screenshot({ path: new URL('./shots/trend_scrub.png', import.meta.url).pathname });
await page.mouse.move(5, 5); await page.waitForTimeout(150);
console.log('left:', (await readout()).replace(/\n+/g, ' '));
console.log('overflow', await page.evaluate(() => document.documentElement.scrollWidth > innerWidth));
await b.close();
