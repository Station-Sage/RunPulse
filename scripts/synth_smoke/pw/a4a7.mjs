import { chromium } from 'playwright';
const BASE = process.env.BASE;
const b = await chromium.launch(); const p = await b.newPage();
let fail = 0;
for (const slug of ['utrs','cirs','rri']) {
  await p.goto(`${BASE}/v2/library/metrics/${slug}`); await p.waitForTimeout(2500);
  const c = await p.locator('[data-testid=breakdown-conclusion]').count();
  const pe = await p.locator('[data-testid=breakdown-personal]').count();
  const f = await p.locator('[data-testid=footer-coach]').count();
  console.log(slug, 'conclusion', c, 'personal', pe, 'footer', f);
  if (!f) fail++;
}
await b.close(); process.exit(fail ? 1 : 0);
