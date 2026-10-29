import { chromium } from '/home/ubuntu/projects/RunPulse/scripts/synth_smoke/pw/node_modules/playwright/index.mjs';
const B = 'http://127.0.0.1:18205/v2';
const b = await chromium.launch({executablePath:'/home/ubuntu/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome'});
const ctx = await b.newContext({ viewport:{width:375,height:812}, locale:'ko-KR' });
const page = await ctx.newPage();
const errs=[]; page.on('pageerror',e=>errs.push(e.message));
let mode='500';
await page.route(/\/api\/v1\/(coach\/plan\/active|coach\/threads|library\/activities\?)/, r => mode==='ok' ? r.continue() : mode==='net' ? r.abort('failed') : r.fulfill({status:500,contentType:'application/json',body:'{"error":{"code":"X","message":"x"}}'}));
for (const [name,path] of [['plan','/coach/plan'],['coach','/coach'],['acts','/library/activities']]) {
  for (const m of ['500','net']) {
    mode=m; await page.goto(B+path,{waitUntil:'networkidle'}); await page.waitForTimeout(500);
    const alert = page.locator('[data-testid=error-state]').first();
    console.log(name,m,'alert',await alert.count(), (await alert.innerText().catch(()=>'')).replace(/\n/g,' | '));
  }
  mode='500'; await page.goto(B+path,{waitUntil:'networkidle'}); await page.waitForTimeout(400);
  mode='ok';
  const rb = page.getByRole('button',{name:'다시 시도'}).first();
  if (await rb.count()) { await rb.click(); await page.waitForTimeout(1000); console.log(name,'after retry alerts',await page.locator('[data-testid=error-state]').count()); }
  await page.screenshot({path:`/tmp/err_${name}.png`});
}
console.log('errs',errs);
await b.close();
