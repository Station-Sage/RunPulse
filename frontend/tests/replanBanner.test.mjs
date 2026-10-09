import test from 'node:test';
import assert from 'node:assert/strict';
import { replanBannerView, replanHref, toastAdvisory, isoWeekStart } from '../src/lib/replanBanner.ts';

const R = { code: 'REPLAN', severity: 'info', text: 'r', link: { distance_km: 42.195, race_date: '2026-12-06', target_time_sec: 12600, recent_weekly_km: 30.5 } };
const Q = { code: 'Q_DROPPED_2', severity: 'caution', text: 'q' };

test('isoWeekStart: 일요일은 직전 월요일', () => {
	assert.equal(isoWeekStart('2026-10-11'), '2026-10-05');
	assert.equal(isoWeekStart('2026-10-05'), '2026-10-05');
});

test('banner: REPLAN 만, 통증·숨김이면 없음', () => {
	assert.equal(replanBannerView([Q, R], null, '2026-10-09', false), R);
	assert.equal(replanBannerView([Q], null, '2026-10-09', false), null);
	assert.equal(replanBannerView([R], null, '2026-10-09', true), null);
	assert.equal(replanBannerView([R], '2026-10-05', '2026-10-09', false), null);
	assert.equal(replanBannerView([R], '2026-09-28', '2026-10-09', false), R);
	assert.equal(replanBannerView(null, null, '2026-10-09', false), null);
});

test('href: 목표(대회일)가 있을 때만 재계획 화면', () => {
	assert.equal(replanHref('', R), '/coach/plan/replan');
	assert.equal(replanHref('/x', R), '/x/coach/plan/replan');
	assert.equal(replanHref('', { ...R, link: undefined }), null);
});

test('toast: 배너가 보였으면 REPLAN 건너뜀', () => {
	assert.equal(toastAdvisory([R, Q], true), 'q');
	assert.equal(toastAdvisory([R, Q], false), 'r');
	assert.equal(toastAdvisory(undefined, false), undefined);
});
