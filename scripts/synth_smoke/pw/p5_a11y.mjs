import { chromium } from '/home/ubuntu/projects/RunPulse/scripts/synth_smoke/pw/node_modules/playwright/index.mjs';
const B='http://127.0.0.1:18207/v2';
const b=await chromium.launch({executablePath:'/home/ubuntu/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome'});
const page=await (await b.newContext({viewport:{width:375,height:812},locale:'ko-KR',timezoneId:'Asia/Seoul'})).newPage();
const T=async(n=300)=>(await page.locator('main').innerText().catch(e=>'ERR')).slice(0,n).replace(/\n+/g,' | ');
const small=()=>page.evaluate(()=>[...document.querySelectorAll('main a,main button,main input,main summary,main textarea')].map(e=>{const r=e.getBoundingClientRect();return [e.tagName,(e.getAttribute('aria-label')||e.innerText||e.id||'').trim().slice(0,18),Math.round(r.width),Math.round(r.height)]}).filter(x=>x[3]<44||x[2]<44));
for (const p of ['/coach/plan/2','/coach/plan/2/session/2026-10-11','/coach/plan/new','/coach/plan/replan']) { await page.goto(B+p,{waitUntil:'networkidle'}); await page.waitForTimeout(500); console.log(p,'small targets', JSON.stringify(await small())); 
 console.log(' unnamed', JSON.stringify(await page.evaluate(()=>[...document.querySelectorAll('main button,main a,main input,main textarea')].filter(e=>!(e.getAttribute('aria-label')||e.innerText.trim()||(e.labels&&e.labels.length))).map(e=>e.outerHTML.slice(0,90)))));
 console.log(' h1/h2', JSON.stringify(await page.evaluate(()=>[...document.querySelectorAll('h1,h2,h3')].map(h=>h.tagName+':'+h.innerText.slice(0,15)))), 'title', await page.title()); }
// loading + error
await page.route('**/api/v1/coach/plan/active**', async r=>{ await new Promise(s=>setTimeout(s,3000)); r.continue(); });
await page.route('**/api/v1/coach/plan/2', async r=>{ await new Promise(s=>setTimeout(s,3000)); r.continue(); });
const nav=page.goto(B+'/coach/plan/2',{waitUntil:'commit'}); await page.waitForTimeout(1200); console.log('LOADING plan', await T(200)); await nav; await page.waitForTimeout(3500);
await page.unroute('**/api/v1/coach/plan/2');
await page.route('**/api/v1/coach/plan/replan/preview**', r=>r.abort()); await page.route('**/api/v1/coach/plan/replan**', r=> r.request().method()==='GET'? r.abort():r.continue());
await page.goto(B+'/coach/plan/replan',{waitUntil:'networkidle'}); await page.waitForTimeout(800); console.log('REPLAN ERR', await T(250));
await page.unroute('**/api/v1/coach/plan/replan**');
await page.goto(B+'/coach/plan/2/session/2026-10-11',{waitUntil:'networkidle'});
await page.route('**/session/**/note', r=>r.abort());
await page.locator('textarea').fill('x'.repeat(5)); await page.getByRole('button',{name:'저장'}).click(); await page.waitForTimeout(800); console.log('NOTE ERR', await T(400));
await page.unroute('**/session/**/note');
await page.getByRole('button',{name:'저장'}).click(); await page.waitForTimeout(800); console.log('NOTE OK', await T(400));
await page.reload({waitUntil:'networkidle'}); console.log('NOTE reload', await page.locator('textarea').inputValue());
await page.locator('textarea').fill(''); console.log('empty-save enabled', await page.getByRole('button',{name:'저장'}).isEnabled());
await page.getByRole('button',{name:'저장'}).click(); await page.waitForTimeout(600); console.log('EMPTY SAVE', await T(300));
await b.close();
