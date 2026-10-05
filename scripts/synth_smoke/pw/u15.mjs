// U15 피드백 시트·동기화 상태 스모크. 환경: BASE
import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:8766';
const b = await chromium.launch();
for (const w of [390, 1280]) {
  const page = await (await b.newContext({ viewport: { width: w, height: 800 } })).newPage();
  const errs = [];
  page.on('pageerror', (e) => errs.push(e.message));
  page.on('console', (m) => m.type() === 'error' && errs.push(m.text()));
  await page.goto(BASE + '/v2/library/19227', { waitUntil: 'networkidle' });
  await page.getByTestId('activity-more').click();
  await page.getByTestId('menu-feedback').click();
  console.log(w, 'sheet', await page.getByTestId('activity-feedback-sheet').count());
  await page.getByLabel('RPE 6', { exact: true }).click({ timeout: 5000 });
  await page.getByText('저장', { exact: false }).last().click().catch((e) => console.log('save btn', e.message));
  await page.waitForTimeout(800);
  console.log(w, 'summary', await page.getByTestId('feedback-summary').count());
  await page.screenshot({ path: `out/u15_${w}.png`, fullPage: false });
  console.log(w, 'errs', JSON.stringify(errs));
}
await b.close();
