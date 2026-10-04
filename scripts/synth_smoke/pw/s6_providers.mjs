// S6 소스 비교 스모크 — 매트릭스·기간 칩·쌍 상세·메트릭 링크. 환경: BASE
import { chromium } from 'playwright';
const BASE = process.env.BASE || 'http://127.0.0.1:18101';
const b = await chromium.launch();
const page = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
const errs = [];
page.on('pageerror', (e) => errs.push('pageerror ' + e.message));
page.on('console', (m) => m.type() === 'error' && errs.push('console ' + m.text()));
const shot = (n) => page.screenshot({ path: new URL(`./shots/s6_${n}.png`, import.meta.url).pathname, fullPage: true });
const ok = (c, m) => { console.log(c ? 'OK  ' : 'FAIL', m); if (!c) process.exitCode = 1; };

await page.goto(BASE + '/v2/library/providers', { waitUntil: 'networkidle' });
ok((await page.title()).includes('소스 비교'), 'title');
ok(await page.getByText('같은 러닝 비교').count() > 0, '섹션: 같은 러닝 비교');
ok(await page.getByText('정의가 달라 비교하지 않는 지표').count() > 0, '섹션: 정의 다른 지표');
ok(await page.getByText('Provider 정체성 매트릭스').count() === 0, '옛 제목 없음');
await shot('matrix');

await page.getByRole('button', { name: '12주' }).click();
await page.waitForFunction(() => location.search.includes('days=84'));
ok(await page.getByRole('button', { name: '12주' }).getAttribute('aria-pressed') === 'true', '12주 칩 활성');
await page.getByRole('button', { name: '4주' }).click();
await page.waitForFunction(() => !location.search.includes('days'));
ok(true, '4주 복귀 시 days 파라미터 제거');

const link = page.locator('a[href*="/library/providers/"]').first();
if (await link.count()) {
  await link.click();
  await page.waitForURL(/\/library\/providers\/[^/?]+/);
  await page.waitForLoadState('networkidle');
  ok(/\/library\/providers\/[^/?]+/.test(page.url()), '쌍 상세 이동 ' + page.url());
  await shot('pairs');
} else console.log('SKIP 쌍 상세 링크 없음(이 기간 쌍 부족)');

await page.goto(BASE + '/v2/library/providers/training_load?days=84', { waitUntil: 'networkidle' });
ok(await page.locator('h1').innerText() === '훈련 부하', 'training_load 상세 제목');
await shot('pairs_tl');
await page.goto(BASE + '/v2/library/providers/nope', { waitUntil: 'networkidle' });
ok(await page.getByText('소스 비교로').count() > 0, '없는 그룹 오류 화면(404 응답은 의도)');

await page.goto(BASE + '/v2/library/metrics/ctl', { waitUntil: 'networkidle' });
ok(await page.getByRole('link', { name: '소스 비교' }).count() > 0, '메트릭 상세 소스 비교 링크');
console.log(errs.length ? 'ERRORS:\n' + errs.join('\n') : 'console/page errors: 0');
await b.close();
