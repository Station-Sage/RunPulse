import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:18099';
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }).catch(()=>chromium.launch());
const errs = [];
for (const w of [1280, 390]) {
  const ctx = await b.newContext({ viewport: { width: w, height: 900 } });
  const p = await ctx.newPage();
  p.on('console', m => m.type()==='error' && errs.push(`[${w}] console: ${m.text()}`));
  p.on('response', r => r.status()>=400 && errs.push(`[${w}] ${r.status()} ${r.url()}`));
  await p.goto(BASE + '/v2/data/export', { waitUntil: 'networkidle' });
  const body = async () => (await p.innerText('body'));
  console.log(w, 'card:', (await body()).includes('구독'));
  const mk = p.getByRole('button', { name: /구독 주소 만들기/ });
  if (await mk.count()) { await mk.click(); await p.waitForTimeout(800); }
  const t = await body();
  console.log(w, 'url shown:', /rpcal_|\/feeds\/cal\//.test(await p.locator('input[readonly]').first().inputValue().catch(()=> '')), 'copy btn:', t.includes('주소 복사'), 'last:', t.includes('가져간 적'));
  const ov = await p.evaluate(() => document.documentElement.scrollWidth > innerWidth);
  console.log(w, 'overflow:', ov);
  if (w === 1280) {
    const rot = p.getByRole('button', { name: /재발급/ });
    if (await rot.count()) { await rot.first().click(); console.log('dialog:', await p.getByRole('alertdialog').count());
      await p.getByRole('button', { name: /취소|아니/ }).first().click().catch(()=>{}); }
    const rv = p.getByRole('button', { name: /해제|끄기|중지/ });
    if (await rv.count()) { await rv.first().click(); console.log('revoke dialog:', await p.getByRole('alertdialog').count());
      await p.getByRole('button', { name: /취소|아니/ }).first().click().catch(()=>{}); }
  }
  await p.screenshot({ path: `shots/cal_${w}.png`, fullPage: true });
  await ctx.close();
}
console.log('errors:', errs);
await b.close();
