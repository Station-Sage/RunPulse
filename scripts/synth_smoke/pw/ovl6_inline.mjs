import { chromium } from '/home/ubuntu/projects/RunPulse/scripts/synth_smoke/pw/node_modules/playwright/index.mjs';
const B = 'http://127.0.0.1:18205/v2';
const b = await chromium.launch({executablePath:'/home/ubuntu/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome'});
const errs=[]; let ok=true; const chk=(n,c)=>{console.log(c?'OK ':'NG ',n); if(!c) ok=false;};
const page = await (await b.newContext({ viewport:{width:375,height:812}, locale:'ko-KR' })).newPage();
page.on('pageerror',e=>errs.push(e.message));
const focusName = ()=>page.evaluate(()=>document.activeElement?.textContent?.trim());
async function flow(label, opener, groupLabel){
  const op = page.getByRole('button',{name:opener}).first();
  if(!(await op.count())){ console.log('SKIP',label,'(opener 없음)'); return; }
  await op.click(); await page.waitForTimeout(300);
  const g = page.locator(`[role=group][aria-label="${groupLabel}"]`);
  chk(label+' group shown', await g.count()===1);
  chk(label+' no alertdialog', await page.locator('[role=alertdialog]').count()===0);
  chk(label+' focus on 취소', (await focusName())==='취소');
  await page.keyboard.press('Escape'); await page.waitForTimeout(300);
  chk(label+' esc cancels', await g.count()===0);
  chk(label+' focus back to opener', (await focusName())===opener || (await focusName()||'').startsWith(opener.replace('…','')));
}
for (const p of ['intervals','strava']) {
  await page.route('**/api/v1/data/sources/'+p, async r=>{ if(r.request().method()!=='GET') return r.continue();
    const res=await r.fetch(); const j=await res.json(); if(j.data) j.data.connection='connected'; await r.fulfill({response:res,json:j}); });
  await page.goto(B+'/data/sources/'+p,{waitUntil:'networkidle'});
  await flow('connect-'+p,'연결 해제…','연결 해제 확인');
}
const H={Origin:'http://127.0.0.1:18205'};
await page.request.post('http://127.0.0.1:18205/api/v1/data/calendar-feed',{data:{rotate:false},headers:H});
await page.request.post('http://127.0.0.1:18205/api/v1/settings/mcp-tokens',{data:{label:'t'},headers:H});
await page.goto(B+'/data/export',{waitUntil:'networkidle'});
await flow('calendar-rotate','주소 재발급','확인');
await flow('calendar-revoke','구독 해제','확인');
await page.goto(B+'/data/settings',{waitUntil:'networkidle'});
await flow('mcp','폐기','폐기 확인');
console.log('pageerrors',errs.length); if(errs.length) ok=false;
await b.close(); process.exit(ok?0:1);
