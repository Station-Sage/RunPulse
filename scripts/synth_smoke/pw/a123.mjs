import { chromium } from 'playwright';
const BASE=process.env.BASE; const b=await chromium.launch(); const p=await (await b.newContext({viewport:{width:1100,height:900}})).newPage();
const errs=[]; p.on('pageerror',e=>errs.push(e.message));
// A-1/A-2: Library home → PB → activity → back
await p.goto(`${BASE}/v2/library`,{waitUntil:'networkidle'});
const pb=p.locator('a[href*="?from=pb"]').first();
console.log('pb links',await p.locator('a[href*="?from=pb"]').count());
if(await pb.count()){ await pb.click(); await p.waitForURL(/from=pb/); console.log('back label',await p.locator('[data-testid=activity-back]').innerText());
 await p.click('[data-testid=activity-back]'); await p.waitForTimeout(800); console.log('after back',p.url()); }
// tab → back uses from path
await p.goto(`${BASE}/v2/library/activities`,{waitUntil:'networkidle'});
await p.locator('a[href*="?from=list"]').first().click(); await p.waitForURL(/from=list/);
await p.click('[data-testid=activity-back]'); await p.waitForTimeout(800); console.log('list back',p.url());
// A-3 wellness source
const r=await p.request.get(`${BASE}/api/v1/library/wellness`).catch(()=>null);
await p.goto(`${BASE}/v2/library/metrics/utrs`,{waitUntil:'networkidle'});
await p.waitForTimeout(1500);
console.log('wellness src',await p.locator('[data-testid=source-wellness]').count(),'act src',await p.locator('[data-testid=source-activity]').count());
if(await p.locator('[data-testid=source-wellness]').count()){await p.locator('[data-testid=source-wellness]').first().click();await p.waitForTimeout(800);console.log(p.url());}
console.log('errors',errs); await b.close();
