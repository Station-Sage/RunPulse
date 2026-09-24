// Coach 홈 QuickInput 체크인 저장 → 새로고침 후 유지 확인. 환경: BASE
import { chromium } from 'playwright';
const b = await chromium.launch(); const page = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
const errs = []; page.on('response', (r) => { if (r.status() >= 400) errs.push(r.status() + ' ' + r.url()); });
await page.goto((process.env.BASE || 'http://127.0.0.1:18099') + '/v2/coach', { waitUntil: 'networkidle' });
console.log('before:', (await page.locator('text=컨디션').allInnerTexts()).join(' | '));
await page.getByText('오늘 컨디션 입력').click();
await page.waitForTimeout(300);
await page.getByRole('button', { name: '피로도 6' }).click();
await page.getByRole('button', { name: '경미' }).click();
await page.getByRole('button', { name: '저장' }).click();
await page.waitForTimeout(800);
console.log('after:', (await page.locator('text=피로').allInnerTexts()).join(' | '));
await page.reload({ waitUntil: 'networkidle' });
console.log('after reload:', (await page.locator('text=피로').allInnerTexts()).join(' | '));
console.log('errors:', errs);
await b.close();
