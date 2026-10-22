import { chromium } from '/home/ubuntu/projects/RunPulse/scripts/synth_smoke/pw/node_modules/playwright/index.mjs';
const B = 'http://127.0.0.1:18205/v2';
const b = await chromium.launch({executablePath:'/home/ubuntu/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome'});
const errs=[]; let ok=true; const chk=(n,c)=>{console.log(c?'OK ':'NG ',n); if(!c) ok=false;};
const page = await (await b.newContext({ viewport:{width:375,height:812}, locale:'ko-KR' })).newPage();
page.on('pageerror',e=>errs.push(e.message));
await page.goto(B+'/coach/plan/1',{waitUntil:'networkidle'});
const btn = page.getByTestId('row-action-btn').first();
if (await btn.count()===0) { console.log('SKIP no row action'); }
else {
  await btn.click(); await page.waitForTimeout(300);
  const sh = page.getByTestId('row-action-sheet');
  chk('sheet open', await sh.count()===1);
  chk('focus inside', await sh.evaluate(n=>n.contains(document.activeElement)));
  chk('scroll locked', await page.evaluate(()=>document.body.style.overflow==='hidden'));
  for (let i=0;i<12;i++) await page.keyboard.press('Tab');
  chk('tab trapped', await sh.evaluate(n=>n.contains(document.activeElement)));
  await page.keyboard.press('Escape'); await page.waitForTimeout(300);
  chk('esc closes', await sh.count()===0);
  chk('focus back to opener', await btn.evaluate(n=>n===document.activeElement));
  chk('scroll unlocked', await page.evaluate(()=>document.body.style.overflow!=='hidden'));
}
console.log('pageerrors',errs.length); if(errs.length) ok=false;
await b.close(); process.exit(ok?0:1);
