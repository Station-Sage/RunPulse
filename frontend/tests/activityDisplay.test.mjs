import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { altCells, otherLine, paceCell, showDistance, timeCell } from '../src/lib/activityDisplay.ts';

const base = { family: 'running', label: '러닝', show_distance: true, pace: null, speed_kmh: null,
	times: { moving_sec: 3000, elapsed_sec: 3000 }, alt_fields: [] };

describe('activityDisplay', () => {
	it('display 없으면 거리 보임·셀 없음', () => {
		assert.equal(showDistance(null), true);
		assert.equal(paceCell(null), null);
		assert.deepEqual(altCells(undefined), []);
	});
	it('수영은 /100m 페이스', () => {
		const c = paceCell({ ...base, family: 'swimming', pace: { value_sec: 125, unit: '/100m', basis: 'moving' } });
		assert.deepEqual(c, { label: '평균 페이스', value: '2:05', unit: '/100m' });
	});
	it('사이클은 km/h', () => {
		const c = paceCell({ ...base, family: 'cycling', speed_kmh: 25.04 });
		assert.deepEqual(c, { label: '평균 속도', value: '25.0', unit: 'km/h' });
	});
	it('이동·총 시간이 다르면 짝으로', () => {
		const c = timeCell({ ...base, times: { moving_sec: 2900, elapsed_sec: 3000 } }, 3000);
		assert.match(c.value, / \/ /);
		assert.equal(timeCell(base, 3000).value, '50:00');
	});
	it('근력은 있는 대체 값만 순서대로', () => {
		const d = { ...base, family: 'strength', show_distance: false,
			alt_fields: [{ key: 'duration', value: 2400 }, { key: 'avg_hr', value: 110 }] };
		assert.equal(showDistance(d), false);
		assert.deepEqual(altCells(d).map((c) => c.label), ['시간', '평균 심박']);
	});
	it('비러닝 한 줄', () => {
		assert.equal(otherLine([]), '');
		assert.equal(otherLine([{ label: '수영', count: 1 }, { label: '근력', count: 2 }]), '그 외 수영 1회 · 근력 2회');
	});
});
