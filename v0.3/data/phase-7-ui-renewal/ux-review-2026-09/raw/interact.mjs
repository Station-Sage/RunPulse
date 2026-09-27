// 읽기 전용 상호작용 측정: 클릭→URL 변화/DOM 변화/네트워크 안정까지 시간, 클릭 기대 요소 반응 여부.
import { createRequire } from 'module';
import fs from 'fs';
const require = createRequire('/home/ubuntu/projects/RunPulse/scripts/synth_smoke/pw/package.json');
const { chromium } = require('playwright');
const OUT = process.env.OUT; const SHOTS = OUT + '/screenshots'; const RAW = process.env.RAW;
const BASE = 'http://localhost:80';
const VP = process.env.VP || 'desktop';
const vpo = VP === 'desktop' ? { viewport: { width: 1280, height: 800 } } : { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 };
const browser = await chromium.launch();
const ctx = await browser.newContext({ ...vpo, locale: 'ko-KR' });
// 인증 헤더는 로컬 서버 요청에만 주입(외부 폰트 CORS 오염 방지)
await ctx.route('http://localhost/**', (route) => route.continue({ headers: { ...route.request().headers(), 'cf-access-authenticated-user-email': 'pansongit@gmail.com' } }));
const page = await ctx.newPage();
await page.addInitScript(() => {
  window.__mut = 0;
  new MutationObserver(() => { if (!window.__mutT) window.__mutT = performance.now(); }).observe(document, { subtree: true, childList: true, characterData: true, attributes: true });
});
const log = [];
const snap = async (name) => { try { await page.screenshot({ path: `${SHOTS}/${name}-${VP}.png`, fullPage: true }); } catch {} };
async function measure(label, locatorFn, { shot, expectNav } = {}) {
  const rec = { label };
  try {
    const loc = locatorFn();
    if (!(await loc.count())) { rec.result = 'NOT_FOUND'; log.push(rec); console.log(JSON.stringify(rec)); return; }
    await loc.first().scrollIntoViewIfNeeded();
    const urlBefore = page.url();
    const txtBefore = await page.evaluate(() => document.body.innerText);
    await page.evaluate(() => { window.__mutT = 0; window.__clickT = performance.now(); });
    const t0 = Date.now();
    const tag = await loc.first().evaluate((e) => e.tagName.toLowerCase() + (e.getAttribute('href') ? ' href=' + e.getAttribute('href') : '') + (e.getAttribute('role') ? ' role=' + e.getAttribute('role') : ''));
    rec.element = tag;
    await loc.first().click({ timeout: 3000 });
    let urlChangeMs = null;
    for (let i = 0; i < 60; i++) { if (page.url() !== urlBefore) { urlChangeMs = Date.now() - t0; break; } await page.waitForTimeout(25); if (!expectNav && i > 12) break; }
    try { await page.waitForLoadState('networkidle', { timeout: 10000 }); } catch {}
    const settledMs = Date.now() - t0;
    await page.waitForTimeout(200);
    const firstMut = await page.evaluate(() => (window.__mutT ? Math.round(window.__mutT - window.__clickT) : null)).catch(() => null);
    const txtAfter = await page.evaluate(() => document.body.innerText).catch(() => '');
    rec.urlBefore = urlBefore.replace(BASE, ''); rec.urlAfter = page.url().replace(BASE, '');
    rec.urlChangeMs = urlChangeMs; rec.firstDomMutationMs = firstMut; rec.settledMs = settledMs;
    rec.textChanged = txtBefore !== txtAfter; rec.textDelta = txtAfter.length - txtBefore.length;
    rec.result = rec.urlAfter !== rec.urlBefore ? 'NAVIGATED' : rec.textChanged ? 'IN_PAGE_CHANGE' : 'NO_VISIBLE_REACTION';
    if (shot) await snap(shot);
  } catch (e) { rec.result = 'ERROR ' + e.message.slice(0, 120); }
  log.push(rec); console.log(JSON.stringify(rec));
}
const go = async (p) => { await page.goto(BASE + p, { waitUntil: 'networkidle' }); await page.waitForTimeout(300); };

// 1) 탭 전환(웜 SPA)
await go('/v2/today');
const nav = () => page.locator('nav[aria-label="주 메뉴"]');
await measure('tab Today→Library', () => nav().getByText('Library', { exact: true }), { expectNav: true });
await measure('tab Library→Coach', () => nav().getByText('Coach', { exact: true }), { expectNav: true });
await measure('tab Coach→Today', () => nav().getByText('Today', { exact: true }), { expectNav: true });
await measure('tab Today→Library (2nd, cached?)', () => nav().getByText('Library', { exact: true }), { expectNav: true });

// 2) Today 상호작용
await go('/v2/today');
await measure('Today: 최근 활동 행(러닝) 클릭', () => page.getByText('9.3km', { exact: false }));
await go('/v2/today');
await measure('Today: UTRS 링 클릭', () => page.getByText('UTRS', { exact: true }), { shot: 'today-utrs-click' });
await go('/v2/today');
await measure('Today: TSB 링 클릭', () => page.getByText('TSB', { exact: true }));
await go('/v2/today');
await measure('Today: 근거 칩 "TSB -15" 클릭', () => page.getByText('TSB -15 (피로 누적)', { exact: false }), { shot: 'today-evidence-chip' });
await go('/v2/today');
await measure('Today: 근거 칩 "CTL 73.9" 클릭', () => page.getByText('CTL 73.9 (월초', { exact: false }));
await go('/v2/today');
await measure('Today: 예측 추이·근거 펼치기', () => page.getByText('예측 추이 · 근거', { exact: false }), { shot: 'today-prediction-expanded' });
await measure('Today: (펼친 뒤) 자체 추정 근거 펼치기', () => page.getByText('자체 추정 근거', { exact: false }), { shot: 'today-prediction-basis' });
await go('/v2/today');
await measure('Today: 예측 기록 3:40:23 클릭', () => page.getByText('3:40:23', { exact: true }));
await go('/v2/today');
await measure('Today: 폼 차트 클릭', () => page.locator('svg:below(:text("체력·피로·폼"))').first());
await go('/v2/today');
await measure('Today: 마일스톤 행 클릭', () => page.getByText('누적 3800km', { exact: false }));
await go('/v2/today');
await measure('Today: 이번 달 전체 이야기', () => page.getByText('이번 달 전체 이야기', { exact: false }), { shot: 'today-month-story' });
await go('/v2/today');
await measure('Today: 전체 마일스톤', () => page.getByText('전체 마일스톤', { exact: false }), { shot: 'today-milestones' });
await go('/v2/today');
await measure('Today: 세션 상세 링크', () => page.getByText('세션 상세', { exact: false }), { expectNav: true });
await go('/v2/today');
await measure('Today: 오늘 컨디션 입력 열기(저장 안 함)', () => page.getByText('오늘 컨디션 입력', { exact: false }), { shot: 'today-checkin-open' });

// 3) Library
await go('/v2/library');
await measure('Library: 최근 활동 행 클릭', () => page.locator('a[href$="/library/17414"]'), { expectNav: true });
await go('/v2/library');
await measure('Library: 히트맵 셀 클릭', () => page.locator('svg rect').nth(200));
await go('/v2/library');
await measure('Library: 월별 막대 클릭', () => page.locator('a[href*="from=2026-08-01"]'), { expectNav: true, shot: 'library-month-filter' });
await go('/v2/library');
await measure('Library: PB 풀 3:41:09', () => page.locator('a[href$="/library/910"]').last(), { expectNav: true, shot: 'activity-910' });
await go('/v2/library/activities');
await measure('Activities: 필터 "하프+"', () => page.getByText('하프+', { exact: true }), { shot: 'library-activities-half' });
await measure('Activities: 더 불러오기', () => page.getByRole('button', { name: /더 불러오기/ }));
await go('/v2/library/activities');
await measure('Activities: 행 클릭', () => page.locator('a[href$="/library/15302"]'), { expectNav: true, shot: 'activity-15302' });
// 활동 상세
await go('/v2/library/17414');
await measure('Activity: 메트릭 카드(훈련 부하) 클릭', () => page.locator('[role=button]', { hasText: '훈련 부하' }), { shot: 'activity-card-click' });
await go('/v2/library/17414');
await measure('Activity: 심박 토글', () => page.getByRole('button', { name: '심박' }), { shot: 'activity-hr-toggle' });
await go('/v2/library/17414');
await measure('Activity: 경로 지도 클릭', () => page.locator('svg[aria-label*="경로"]'));
await go('/v2/library/17414');
await measure('Activity: 스플릿 바 클릭', () => page.getByText('6:33/km', { exact: true }));
await go('/v2/library/17414');
await measure('Activity: 서브탭 랩', () => page.locator('a[href$="/17414/laps"]').first(), { expectNav: true });
await measure('Activity: 서브탭 메트릭', () => page.locator('a[href$="/17414/metrics"]').first(), { expectNav: true });
await measure('Activity: 메트릭 행 VDOT 클릭', () => page.getByText('RunPulse VDOT', { exact: false }), { shot: 'activity-metric-vdot' });
await go('/v2/library/17414/metrics');
await measure('Activity: 서브탭 스트림', () => page.locator('a[href$="/17414/streams"]').first(), { expectNav: true });
await measure('Activity: 서브탭 소스 비교', () => page.locator('a[href$="/17414/providers"]').first(), { expectNav: true });
// 메트릭
await go('/v2/library/metrics');
await measure('Metrics: 마라톤 예측 클릭', () => page.locator('a[href$="/metrics/race_pred_marathon_sec"]'), { expectNav: true, shot: 'metric-race_pred_marathon' });
await measure('Metric: 1년 기간', () => page.getByRole('button', { name: '1년' }), { shot: 'metric-race_pred_marathon-1y' });
await measure('Metric: 계산 분해 보기', () => page.getByText('계산 분해 보기', { exact: false }), { shot: 'metric-race_pred_marathon-breakdown' });
await go('/v2/library/metrics/utrs');
await measure('Metric UTRS: 계산 분해 보기', () => page.getByText('계산 분해 보기', { exact: false }), { shot: 'metric-utrs-breakdown' });
await go('/v2/library/metrics/utrs');
await measure('Metric UTRS: 차트 클릭', () => page.locator('svg').first());
await go('/v2/library/metrics/acwr'); await snap('metric-acwr');
await go('/v2/library/metrics/ctl'); await snap('metric-ctl');
await go('/v2/library/metrics/sleep_deep_sec'); await snap('metric-sleep_deep_sec');
await go('/v2/library/metrics/marathon_shape'); await snap('metric-marathon_shape');
await go('/v2/library/metrics');
await measure('Metrics: 심박 세부 지표 펼치기', () => page.getByText('심박 (7)', { exact: false }), { shot: 'library-metrics-hr-expanded' });
await go('/v2/library/metrics');
await measure('Metrics: 카테고리 칩 레이스 준비도', () => page.getByRole('button', { name: '레이스 준비도' }));
// 웰니스/프로바이더
await go('/v2/library/wellness');
await measure('Wellness: 첫 수치 클릭', () => page.locator('main').getByText('수면', { exact: false }));
await go('/v2/library/providers');
await measure('Providers: 12주', () => page.getByRole('button', { name: '12주' }));
// Coach
await go('/v2/coach');
await measure('Coach: 스레드 열기', () => page.locator('a[href$="/coach/4"]'), { expectNav: true });
await measure('Coach thread: 근거 칩 TSB', () => page.locator('button', { hasText: 'TSB -11' }), { shot: 'coach-thread-evidence' });
await go('/v2/coach');
await measure('Coach: 계획 카드 열기', () => page.locator('a[href$="/coach/plan/1"]'), { expectNav: true });
await measure('Plan: ACWR 칩 클릭', () => page.getByRole('button', { name: /ACWR/ }), { shot: 'coach-plan-acwr' });
await go('/v2/coach/plan/1');
await measure('Plan: 세션 행 클릭(9/26)', () => page.locator('a[href$="/session/2026-09-26"]').first(), { expectNav: true });
await go('/v2/coach');
await measure('Coach: 오늘 컨디션 입력 열기(저장 안 함)', () => page.getByText('오늘 컨디션 입력', { exact: false }), { shot: 'coach-checkin-open' });
await go('/v2/coach/plan/new');
await measure('PlanNew: 마라톤 선택(생성 안 함)', () => page.getByRole('button', { name: '마라톤' }), { shot: 'coach-plan-new-marathon' });

fs.writeFileSync(`${RAW}/interact-${VP}.json`, JSON.stringify(log, null, 1));
await browser.close();
