import { chromium } from '/home/ubuntu/projects/RunPulse/scripts/synth_smoke/pw/node_modules/playwright/index.mjs';
const b = await chromium.launch({ executablePath: '/home/ubuntu/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome' });
const ctx = await b.newContext({ viewport: { width: 375, height: 800 } });
const page = await ctx.newPage();
await page.route('**/api/**', (r) => r.request().method() === 'GET' || !r.request().url().includes('/ai') ? r.continue() : r.fulfill({ status: 500, contentType: 'application/json', body: '{"error":"fail"}' }));
await page.goto('http://127.0.0.1:18205/v2/data/settings/ai');
await page.waitForTimeout(1500);
console.log('regions', await page.locator('[data-testid=live-region] [aria-live]').count(), 'initial alert text:', JSON.stringify(await page.locator('[data-testid=live-region] [role=alert]').innerText()));
await page.locator('input[type=password], input[type=text]').first().fill('sk-test-123');
const btn = page.getByRole('button', { name: '저장', exact: true }).first();
if (await btn.count()) { await btn.click(); await page.waitForTimeout(500); }
console.log('page p:', JSON.stringify(await page.locator('main p').allInnerTexts()));
console.log('polite:', JSON.stringify(await page.locator('[data-testid=live-region] [role=status]').innerText()));
console.log('assertive:', JSON.stringify(await page.locator('[data-testid=live-region] [role=alert]').innerText()), 'roles on page:', await page.locator('main [role=alert], main [role=status]').count());
await b.close();
