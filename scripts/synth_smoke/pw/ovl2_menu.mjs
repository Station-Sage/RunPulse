import { chromium } from '/home/ubuntu/projects/RunPulse/scripts/synth_smoke/pw/node_modules/playwright/index.mjs';
const B = 'http://127.0.0.1:18205/v2';
const b = await chromium.launch({executablePath:'/home/ubuntu/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome'});
const page = await (await b.newContext({ viewport:{width:375,height:812}, locale:'ko-KR' })).newPage();
const errs=[]; page.on('pageerror',e=>errs.push(e.message));
await page.goto(B+'/today',{waitUntil:'networkidle'});
const btn = page.getByRole('button',{name:'메뉴'});
await btn.focus(); await btn.click();
const dlg = page.getByRole('dialog',{name:'메뉴'});
await dlg.waitFor();
const st = () => page.evaluate(()=>({ov:document.body.style.overflow, act:document.activeElement?.getAttribute('aria-label')||document.activeElement?.textContent?.trim().slice(0,20), inside: !!document.activeElement?.closest('[role=dialog]')}));
console.log('open', await st());
let outside=0;
for (let i=0;i<40;i++){ await page.keyboard.press('Tab'); if(!(await st()).inside) outside++; }
console.log('tab outside count', outside);
for (let i=0;i<5;i++){ await page.keyboard.press('Shift+Tab'); if(!(await st()).inside) outside++; }
console.log('shift-tab outside', outside);
await page.keyboard.press('Escape');
await dlg.waitFor({state:'detached'});
console.log('after esc', await st(), 'focus-menu-btn', await btn.evaluate(e=>e===document.activeElement));
await btn.click(); await dlg.waitFor();
await page.mouse.click(360,400);
await dlg.waitFor({state:'detached'});
console.log('backdrop closed; overflow', JSON.stringify((await st()).ov));
console.log('errs',errs);
await b.close();
