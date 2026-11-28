import { chromium } from '/home/ubuntu/projects/RunPulse/scripts/synth_smoke/pw/node_modules/playwright/index.mjs';
const B='http://127.0.0.1:18207/v2';
const b=await chromium.launch({executablePath:'/home/ubuntu/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome'});
const page=await (await b.newContext({viewport:{width:375,height:812},locale:'ko-KR',timezoneId:'Asia/Seoul'})).newPage();
const reqs=[]; page.on('request',r=>{ if(r.url().includes('/api/')&&r.method()!=='GET') reqs.push(r.method()+' '+r.url().split('/api/v1')[1].slice(0,60)+' '+(r.postData()||'').slice(0,100));});
const T=async(n=420)=>(await page.locator('main').innerText()).slice(0,n).replace(/\n+/g,' | ');
for (const d of ['2026-10-11','2026-11-16','2026-11-18','2026-10-05']) { await page.goto(B+'/coach/plan/2/session/'+d,{waitUntil:'networkidle'}); console.log(d, await T(260)); }
// today's plan page: click the long-run row
await page.goto(B+'/coach/plan/2',{waitUntil:'networkidle'});
const rows=page.locator('main a[href*="/session/"]'); console.log('row links', await rows.count());
console.log('ACWR btn', await page.getByText('적정 0.8').count());
// replan
await page.goto(B+'/coach/plan/replan',{waitUntil:'networkidle'}); await page.waitForTimeout(800);
console.log('REPLAN', await T(700));
await page.screenshot({path:'/home/ubuntu/projects/RunPulse/scripts/synth_smoke/shots/p5_replan_375.png',fullPage:true});
const apply=page.getByRole('button',{name:/적용/}); 
await apply.dblclick(); await page.waitForTimeout(2000);
console.log('APPLIED', await T(500), JSON.stringify(reqs));
await page.getByRole('button',{name:'되돌리기'}).click(); await page.waitForTimeout(1500);
console.log('UNDO', await T(300), JSON.stringify(reqs));
// replan with no active plan equivalent: direct hit undo twice
await b.close();
