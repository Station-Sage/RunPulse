import { chromium } from 'playwright';
const BASE='http://localhost:5199', API='http://localhost:18098';
const b=await chromium.launch(); const ctx=await b.newContext({viewport:{width:390,height:800}});
await ctx.route('**/api/v1/**', r=>r.continue({url:r.request().url().replace(/^https?:\/\/[^/]+/,API)}));
const p=await ctx.newPage(); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
for (const [path,from] of [['/v2/library','home'],['/v2/library/activities','list'],['/v2/today','today']]) {
  await p.goto(`${BASE}${path}`,{waitUntil:'networkidle'});
  const rows=p.locator('[data-testid=activity-row]'); const n=await rows.count();
  const href=n?await rows.first().getAttribute('href'):null;
  console.log(path,'rows',n,href, href&&href.endsWith(`?from=${from}`)?'ok':'FAIL');
  if(n) await p.screenshot({path:`shots/activity_row_${from}.png`});
}
await p.goto(`${BASE}/v2/library/activities`,{waitUntil:'networkidle'});
await p.locator('[data-testid=activity-row]').first().click(); await p.waitForURL(/library\/\d+/);
console.log('상세 이동',p.url());
console.log('errors',errs.length, errs.slice(0,3)); await b.close();
