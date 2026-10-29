import { chromium } from '/home/ubuntu/projects/RunPulse/scripts/synth_smoke/pw/node_modules/playwright/index.mjs';
const b = await chromium.launch({ executablePath: '/home/ubuntu/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome' });
const p = await (await b.newContext({ viewport: { width: 375, height: 800 } })).newPage();
await p.goto('http://127.0.0.1:18205/v2/library/metrics/ctl', { waitUntil: 'networkidle' }).catch(()=>{});
const s = p.locator('[role=slider]').first();
console.log('sliders', await p.locator('[role=slider]').count());
if (await s.count()) { await s.focus(); await p.keyboard.press('ArrowLeft'); await p.keyboard.press('ArrowLeft'); console.log(await s.getAttribute('aria-valuetext')); }
await b.close();
