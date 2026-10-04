import { chromium } from 'playwright';
const BASE='http://localhost:5199', API='http://localhost:18098';
const b=await chromium.launch(); const ctx=await b.newContext({viewport:{width:1100,height:900}});
await ctx.route('**/api/v1/**', r=>r.continue({url:r.request().url().replace(/^https?:\/\/[^/]+/,API)}));
const p=await ctx.newPage(); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
await p.goto(`${BASE}/v2/library/metrics/ctl?period=1y`,{waitUntil:'networkidle'});
console.log('markers',await p.locator('[data-testid=trend-event]').count());
await p.screenshot({path:'shots/trend_events.png'}); console.log('errors',errs.length); await b.close();
