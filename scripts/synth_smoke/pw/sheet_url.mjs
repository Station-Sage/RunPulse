// ?sheet=row-<id> 딥링크 스모크 (열기→URL, 새로고침 복원, 닫기→URL 제거). 환경: BASE
import { chromium } from 'playwright';
const b = await chromium.launch(); const page = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
const errs = []; page.on('pageerror', (e) => errs.push(e.message));
const B = (process.env.BASE || 'http://127.0.0.1:18112') + '/v2';
await page.goto(B + '/coach/plan/1', { waitUntil: 'networkidle' });
await page.getByTestId('row-action-btn').first().click();
await page.getByTestId('row-action-sheet').waitFor();
await page.waitForTimeout(500);
const url1 = page.url(); console.log('open url:', url1);
await page.reload({ waitUntil: 'networkidle' });
console.log('restored after reload:', await page.getByTestId('row-action-sheet').count());
await page.getByRole('button', { name: '취소' }).click();
await page.waitForTimeout(500);
console.log('closed url has sheet (expect false):', page.url().includes('sheet='), 'sheet count', await page.getByTestId('row-action-sheet').count());
await page.goto(B + '/coach/plan/1?sheet=row-999999', { waitUntil: 'networkidle' });
console.log('unknown id opens nothing (expect 0):', await page.getByTestId('row-action-sheet').count());
console.log('errors:', errs);
await b.close();
