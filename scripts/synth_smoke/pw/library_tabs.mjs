import { chromium } from 'playwright';
const BASE='http://localhost:5199', API='http://localhost:18098';
const b=await chromium.launch(); const ctx=await b.newContext({viewport:{width:420,height:800}});
await ctx.route('**/api/v1/**', r=>r.continue({url:r.request().url().replace(/^https?:\/\/[^/]+/,API)}));
const p=await ctx.newPage(); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
for (const [path,active,tabs] of [['/library','활동',1],['/library/activities','활동',1],['/library/metrics','메트릭',1],['/library/wellness','웰니스',1],['/library/providers','소스 비교',1],['/library/metrics/utrs','',0]]) {
  await p.goto(`${BASE}/v2${path}`,{waitUntil:'networkidle'});
  const nav=p.locator('nav[aria-label="Library 섹션"]');
  const n=await nav.count();
  const cur=n?await nav.locator('[aria-current=page]').innerText():'';
  console.log(path, n===tabs?'ok':'FAIL tabs='+n, 'active=',cur, cur===active?'ok':'FAIL');
}
await p.goto(`${BASE}/v2/library/metrics`,{waitUntil:'networkidle'});
await p.screenshot({path:'shots/library_tabs.png'});
console.log('errors',errs.length); await b.close();
