import { chromium } from 'playwright';
const b = await chromium.launch();
const page = await (await b.newContext({ viewport: { width: 390, height: 900 }, deviceScaleFactor: 2 })).newPage();
await page.goto((process.env.BASE || 'http://127.0.0.1:18101') + '/v2/today', { waitUntil: 'networkidle' });
await page.waitForTimeout(800);
await page.screenshot({ path: 'shots/racehub_top.png', clip: { x: 0, y: 0, width: 390, height: 900 } });
await b.close();
