import { chromium } from '/home/ubuntu/projects/RunPulse/scripts/synth_smoke/pw/node_modules/playwright/index.mjs';
const B = 'http://127.0.0.1:18205/v2';
const b = await chromium.launch({executablePath:'/home/ubuntu/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome'});
for (const [name, vp] of [['m', {width:375,height:812}], ['d', {width:1280,height:800}]]) {
  const page = await (await b.newContext({ viewport: vp, locale:'ko-KR', timezoneId:'Asia/Seoul' })).newPage();
  const errs = []; page.on('response', r => { if (r.status() >= 400) errs.push(r.status()+' '+r.url()); });
  page.on('pageerror', e => errs.push('pageerror '+e.message));
  for (const p of ['/coach/plan','/coach/plan/1','/coach/plan/1/session/2026-10-06','/coach/plan/1/session/2026-10-11','/coach/plan/1/session/2026-11-22','/coach/plan/1/session/2026-12-25','/coach/plan/999','/coach/plan/new','/coach/plan/compare','/coach/plan/compare?distance_km=-5&race_date=garbage','/coach/plan/replan']) {
    const t0 = Date.now();
    await page.goto(B+p, { waitUntil:'networkidle' }); await page.waitForTimeout(500);
    const txt = (await page.locator('main').innerText().catch(()=> '')).replace(/\n+/g,' | ').slice(0, 900);
    const ov = await page.evaluate(() => [document.documentElement.scrollWidth, innerWidth, location.pathname]);
    console.log(`\n[${name}] ${p} -> ${ov[2]} ovf=${ov[0]>ov[1]} ${Date.now()-t0}ms\n  ${txt}`);
  }
  console.log(name, 'errs', errs);
}
await b.close();
