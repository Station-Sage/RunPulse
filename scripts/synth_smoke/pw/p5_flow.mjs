import { chromium } from '/home/ubuntu/projects/RunPulse/scripts/synth_smoke/pw/node_modules/playwright/index.mjs';
const B='http://127.0.0.1:18207/v2';
const b=await chromium.launch({executablePath:'/home/ubuntu/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome'});
const ctx=await b.newContext({viewport:{width:375,height:812},locale:'ko-KR',timezoneId:'Asia/Seoul'});
const page=await ctx.newPage();
const reqs=[]; page.on('request',r=>{ if(r.url().includes('/api/')&&r.method()!=='GET') reqs.push(r.method()+' '+r.url().split('/api/v1')[1].slice(0,60)+' '+(r.postData()||'').slice(0,120));});
page.on('dialog',d=>{reqs.push('DIALOG '+d.message()); d.dismiss();});
// compare double click
await page.goto(B+'/coach/plan/compare?distance_km=42.195&race_date=2026-11-22',{waitUntil:'networkidle'});
const sel=page.getByRole('button',{name:'이 프로그램 선택'});
console.log('compare cards', await sel.count());
console.log((await page.locator('main').innerText()).slice(0,400).replace(/\n+/g,' | '));
await sel.nth(0).dblclick(); await page.waitForTimeout(2500);
console.log('after select ->', page.url().replace(B,''), JSON.stringify(reqs));
console.log((await page.locator('main').innerText()).slice(0,300).replace(/\n+/g,' | '));
// session detail interactions
await page.goto(B+'/coach/plan',{waitUntil:'networkidle'});
console.log('new plan landing', page.url().replace(B,''));
console.log((await page.locator('main').innerText()).slice(0,260).replace(/\n+/g,' | '));
await b.close();
