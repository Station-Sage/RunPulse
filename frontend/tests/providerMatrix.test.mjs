import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cellText, parseDays, periodHref, rowHref, pairSeries, visibleProviders } from '../src/lib/providerMatrix.ts';

const row = { format: 'int', unit: 'W', href_group: 'normalized_power' };

test('parseDays: 허용값 외에는 28', () => {
	assert.equal(parseDays('56'), 56);
	assert.equal(parseDays('7'), 28);
	assert.equal(parseDays(null), 28);
});

test('periodHref: 28은 파라미터 제거, 다른 쿼리 보존', () => {
	assert.equal(periodHref('?days=56', 28), '?');
	assert.equal(periodHref('', 84), '?days=84');
	assert.equal(periodHref('?x=1&days=56', 84), '?x=1&days=84');
});

test('cellText: 중앙값 / stale 시 최신값+안내 / 없음', () => {
	assert.deepEqual(cellText(row, undefined), { main: '—', note: null });
	assert.equal(cellText(row, { median: 201.6, latest: 200, last_date: '2026-09-30', stale: false, estimated: false, n: 5 }).main, '202');
	const st = cellText(row, { median: null, latest: 188, last_date: '2026-05-08', stale: true, estimated: false, n: 0 });
	assert.equal(st.main, '188');
	assert.equal(st.note, '5/8 이후 없음');
});

test('rowHref: href_group 없으면 null', () => {
	assert.equal(rowHref('/v2', row, 56), '/v2/library/providers/normalized_power?days=56');
	assert.equal(rowHref('/v2', { href_group: null }, 28), null);
});

test('pairSeries: 날짜 오름차순·x 정규화·값 없는 점 제외', () => {
	const s = pairSeries(
		[
			{ date: '2026-09-02', values: {}, diff_pct: 4, outlier: false, canonical_id: 1, name: null, distance_m: null },
			{ date: '2026-09-01', values: {}, diff_pct: -3, outlier: true, canonical_id: 2, name: null, distance_m: null }
		],
		'same'
	);
	assert.deepEqual(s.map((p) => [p.x, p.y, p.outlier]), [[0, -3, true], [1, 4, false]]);
	assert.deepEqual(pairSeries([], 'scale'), []);
});

test('visibleProviders: 값이 있는 소스만', () => {
	assert.deepEqual(visibleProviders(['garmin', 'strava'], [{ cells: { garmin: {} } }]), ['garmin']);
});
