import test from 'node:test';
import assert from 'node:assert/strict';
import { toApiFilters, jumpLoadCount, nearestMonth, weekMap, shiftMonth } from '../src/lib/activityListQuery.ts';

const base = { preset: 'all', month: '', from: undefined, to: undefined, sport: '', type: '', sort: '', distMin: '', q: '' };

test('toApiFilters: 기본값은 모두 생략', () => {
	assert.deepEqual(JSON.parse(JSON.stringify(toApiFilters(base))), {});
});

test('toApiFilters: 월 모드는 month 만, 기간 모드는 to 에 시각을 붙인다', () => {
	const m = toApiFilters({ ...base, month: '2026-08', from: '2026-08-01', to: '2026-08-31', sport: 'running', type: 'long', sort: 'load' });
	assert.equal(m.month, '2026-08');
	assert.equal(m.from, undefined);
	assert.equal(m.to, undefined);
	assert.equal(m.sport_group, 'running');
	assert.equal(m.sort, 'load');
	const p = toApiFilters({ ...base, preset: null, from: '2026-09-01', to: '2026-09-30', distMin: '10', q: 'x' });
	assert.equal(p.to, '2026-09-30 23:59:59');
	assert.equal(p.dist_min, 10);
	assert.equal(p.q, 'x');
});

const months = [
	{ month: '2026-10', n: 30 },
	{ month: '2026-09', n: 25 },
	{ month: '2026-07', n: 10 }
];

test('jumpLoadCount: 대상 월 끝까지 per 단위 올림', () => {
	assert.equal(jumpLoadCount(months, '2026-10'), 40);
	assert.equal(jumpLoadCount(months, '2026-09'), 80); // 55 → 80
	assert.equal(jumpLoadCount(months, '2026-08'), 80); // 8월 없음 → 7월 포함 65 → 80
	assert.equal(jumpLoadCount(months, '2020-01'), 0);
});

test('nearestMonth', () => {
	assert.equal(nearestMonth(months, '2026-08'), '2026-07');
	assert.equal(nearestMonth(months, '2020-01'), null);
});

test('weekMap / shiftMonth', () => {
	const m = weekMap([{ start: '2026-08-31', n: 2, km: 10, sec: 3000, in_range_only: true }]);
	assert.equal(m.get('2026-08-31').inRangeOnly, true);
	assert.equal(weekMap(undefined).size, 0);
	assert.equal(shiftMonth('2026-01', -1), '2025-12');
	assert.equal(shiftMonth('2026-12', 1), '2027-01');
});
