import { chromium } from '/home/ubuntu/projects/RunPulse/scripts/synth_smoke/pw/node_modules/playwright/index.mjs';
const B = 'http://127.0.0.1:18205/v2';
const b = await chromium.launch({executablePath:'/home/ubuntu/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome'});
const errs=[]; let ok=true; const chk=(n,c)=>{console.log(c?'OK ':'NG ',n); if(!c) ok=false;};
const ctx = await b.newContext({ viewport:{width:375,height:812}, locale:'ko-KR' });
await ctx.addInitScript(()=>sessionStorage.setItem('runpulse.demo','1'));
const page = await ctx.newPage();
page.on('pageerror',e=>errs.push(e.message));
await page.goto(B+'/today',{waitUntil:'networkidle'});
chk('banner shown', await page.getByTestId('demo-banner').count()===1);
const sheet = page.getByTestId('demo-write-sheet');
const blockWrite = ()=>page.evaluate(()=>fetch('/api/v1/goals',{method:'POST'}));
const label = ()=>page.evaluate(()=>document.activeElement?.textContent?.trim());
// 1) 배너 버튼에서 연 경우: Esc 후 그 버튼으로 복귀
const start = page.getByRole('button',{name:'내 데이터로 시작'});
await start.focus(); await blockWrite(); await page.waitForTimeout(300);
chk('sheet open', await sheet.count()===1);
chk('focus inside sheet', await sheet.evaluate(n=>n.contains(document.activeElement)));
chk('scroll locked', await page.evaluate(()=>document.body.style.overflow==='hidden'));
await page.keyboard.press('Escape'); await page.waitForTimeout(300);
chk('esc closes (focus in sheet)', await sheet.count()===0);
chk('focus back to opener', (await label())==='내 데이터로 시작');
chk('scroll unlocked', await page.evaluate(()=>document.body.style.overflow!=='hidden'));
// 2) 포커스가 시트 밖(body)에 있어도 Esc 로 닫힘
await blockWrite(); await page.waitForTimeout(300);
await page.evaluate(()=>document.activeElement?.blur());
await page.keyboard.press('Escape'); await page.waitForTimeout(300);
chk('esc closes (focus outside)', await sheet.count()===0);
// 3) 계속 둘러보기 / 백드롭
await blockWrite(); await page.waitForTimeout(300);
await page.getByRole('button',{name:'계속 둘러보기'}).click(); await page.waitForTimeout(300);
chk('continue closes', await sheet.count()===0);
console.log('pageerrors',errs.length); if(errs.length) ok=false;
await b.close(); process.exit(ok?0:1);
