// 화면별 svg/체크박스/빈 상태 문구 개수 — '에러는 없는데 아무것도 안 그려지는' 화면을 찾는다. 환경: BASE
import { chromium } from 'playwright';
const b = await chromium.launch();
const page = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
const routes = ['/v2/today','/v2/library','/v2/library/activities','/v2/library/100','/v2/library/100/streams','/v2/library/100/laps','/v2/library/100/metrics','/v2/library/100/providers','/v2/library/metrics','/v2/library/metrics/ctl','/v2/library/metrics/utrs','/v2/library/wellness','/v2/library/providers','/v2/coach','/v2/coach/1','/v2/coach/plan/1','/v2/coach/plan/compare'];
for (const r of routes) {
  await page.goto((process.env.BASE || 'http://127.0.0.1:18099') + r, { waitUntil: 'networkidle' });
  await page.waitForTimeout(500);
  const info = await page.evaluate(() => ({
    svg: document.querySelectorAll('svg').length,
    poly: document.querySelectorAll('polyline,path,rect').length,
    cb: [...document.querySelectorAll('input[type=checkbox]')].filter(i => i.checked).length + '/' + document.querySelectorAll('input[type=checkbox]').length,
    len: document.body.innerText.length,
    empty: (document.body.innerText.match(/데이터 (수집 중|없음)|불러올 수 없습니다|준비 중/g) || []).length,
  }));
  console.log(r.padEnd(32), JSON.stringify(info));
}
await b.close();
