import { createRequire } from 'module';
const require = createRequire('/home/ubuntu/projects/RunPulse/scripts/synth_smoke/pw/package.json');
const { chromium } = require('playwright');
const b = await chromium.launch(); const ctx = await b.newContext({ viewport: { width: 1280, height: 800 } });
await ctx.route('http://localhost/**', (r) => r.continue({ headers: { ...r.request().headers(), 'cf-access-authenticated-user-email': 'pansongit@gmail.com' } }));
const p = await ctx.newPage(); await p.goto('http://localhost/v2/today', { waitUntil: 'networkidle' });
const chips = await p.evaluate(() => [...document.querySelectorAll('span.rounded-full, button.rounded-full')].map(e => e.tagName + ':' + JSON.stringify(e.innerText)));
console.log(chips.join('\n'));
const btn = p.locator('button.rounded-full').first();
if (await btn.count()) { const before = await p.evaluate(() => document.body.innerText.length); await btn.click(); await p.waitForTimeout(500); console.log('clicked', await btn.innerText(), 'delta', (await p.evaluate(() => document.body.innerText.length)) - before); await p.screenshot({ path: process.env.OUT + '/screenshots/today-evidence-chip-desktop.png', fullPage: true }); }
await b.close();
