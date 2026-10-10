import { chromium } from 'playwright';
const BASE=process.env.BASE||'http://127.0.0.1:5099';
const b=await chromium.launch();
for (const [name,w,h] of [['desk',1100,900],['m390',390,844]]) {
  const ctx=await b.newContext({viewport:{width:w,height:h}});
  const p=await ctx.newPage();
  await p.goto(`${BASE}/v2/library/metrics/ctl`,{waitUntil:'networkidle'});
  await p.getByRole('button',{name:/1년/}).first().click(); await p.waitForTimeout(500);
  const bb=await p.locator('[data-testid="trend-event"]').filter({hasText:'◆'}).first().boundingBox();
  const cx=bb.x+bb.width/2; let hit=null;
  for (let dx=-8;dx<=8&&hit===null;dx++){ await p.mouse.move(cx+dx,bb.y-30); await p.waitForTimeout(80);
    const t=await p.locator('[data-testid="trend-event-readout"]').allInnerTexts(); if(t.length) hit=dx; }
  console.log(name,'hit dx',hit,await p.locator('[data-testid="trend-event-readout"]').allInnerTexts(),await p.locator('[data-testid="trend-event-reason"]').allInnerTexts());
  await p.screenshot({path:`/tmp/diamond2_${name}.png`,clip:{x:0,y:230,width:w,height:300}});
}
await b.close();
