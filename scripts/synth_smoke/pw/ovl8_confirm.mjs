import { chromium } from '/home/ubuntu/projects/RunPulse/scripts/synth_smoke/pw/node_modules/playwright/index.mjs';
const B = 'http://127.0.0.1:18205/v2';
const b = await chromium.launch({executablePath:'/home/ubuntu/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome'});
const errs=[]; let ok=true; const chk=(n,c)=>{console.log(c?'OK ':'NG ',n); if(!c) ok=false;};
const ctx = await b.newContext({ viewport:{width:375,height:812}, locale:'ko-KR' });
const page = await ctx.newPage();
page.on('pageerror',e=>errs.push(e.message));
await page.route('**/api/v1/coach/plan/restorable',async r=>{
  const res=await r.fetch(); const j=await res.json().catch(()=>({}));
  await r.fulfill({response:res,json:{...j,ok:true,data:{plans:[{goal_id:77,name:'테스트 플랜',distance_km:42.2,race_date:'2099-01-01',rows:9}]}}});
});
await page.goto(B+'/coach/plan?past',{waitUntil:'networkidle'});
const active = ()=>page.evaluate(()=>document.activeElement?.textContent?.trim());
const open = page.locator('#restore-open-77');
if (await open.count()===0) { console.log('SKIP no restorable (body):', (await page.textContent('body')).slice(0,200)); }
else {
  await open.click(); await page.waitForTimeout(200);
  const g = page.getByTestId('restore-confirm');
  chk('group role', (await g.getAttribute('role'))==='group');
  chk('focus on 취소', (await active())==='취소');
  await page.keyboard.press('Escape'); await page.waitForTimeout(300);
  chk('esc closes', await g.count()===0);
  chk('focus back to opener', (await active())==='복원하기');
}
await page.route('**/api/v1/coach/plan/replan/last',async r=>{
  const res=await r.fetch(); const j=await res.json();
  const last={replan_id:5,anchor_monday:'2099-01-05'};
  await r.fulfill({response:res,json:{...j,data:{entry:{eligible:true,last,reason:null},last}}});
});
await page.goto(B+'/coach/plan/1',{waitUntil:'networkidle'});
const ub = page.getByRole('button',{name:'되돌리기',exact:true});
if (await ub.count()===0) console.log('SKIP undo opener');
else {
  await ub.click(); await page.waitForTimeout(200);
  const g = page.getByTestId('undo-confirm');
  chk('undo group role', (await g.getAttribute('role'))==='group');
  chk('undo focus 취소', (await active())==='취소');
  await page.keyboard.press('Escape'); await page.waitForTimeout(300);
  chk('undo esc closes', await g.count()===0);
  chk('undo focus back', (await active())==='되돌리기');
}
console.log('pageerrors',errs.length); if(errs.length) ok=false;
await b.close(); process.exit(ok?0:1);
