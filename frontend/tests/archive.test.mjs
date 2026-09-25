import { test } from 'node:test';
import assert from 'node:assert/strict';
import { heatLevel, buildHeatmap, monthHeights, monthRange } from '../src/lib/archive.ts';

test('heatLevel 경계', () => {
	assert.equal(heatLevel(0), 0);
	assert.equal(heatLevel(0.1), 1);
	assert.equal(heatLevel(5), 1);
	assert.equal(heatLevel(5.1), 2);
	assert.equal(heatLevel(10), 2);
	assert.equal(heatLevel(18), 3);
	assert.equal(heatLevel(24.2), 4);
});

test('buildHeatmap: 마지막 셀이 endDate, 열=주·행=요일(월=0)', () => {
	// 2026-09-24는 목요일(행 3)
	const h = buildHeatmap([{ date: '2026-09-24', km: 10 }], '2026-09-24', 53);
	const last = h.cells[h.cells.length - 1];
	assert.equal(last.date, '2026-09-24');
	assert.equal(last.row, 3);
	assert.equal(last.col, 52);
	assert.equal(last.level, 2);
	// 첫 셀은 월요일, 열 0
	assert.equal(h.cells[0].row, 0);
	assert.equal(h.cells[0].col, 0);
	// 마지막 주는 목요일까지만(미래 없음): 마지막 열의 셀 4개
	assert.equal(h.cells.filter((c) => c.col === 52).length, 4);
	assert.equal(h.columns, 53);
});

test('buildHeatmap: 데이터 없는 날은 level 0, 월 라벨은 달이 바뀔 때', () => {
	const h = buildHeatmap([], '2026-09-24', 53);
	assert.ok(h.cells.every((c) => c.level === 0));
	assert.ok(h.months.length >= 12);
	assert.equal(h.months[0].col, 0);
	assert.match(h.months[0].label, /^\d+월$/);
});

test('monthHeights: 최댓값 기준 정규화', () => {
	assert.deepEqual(monthHeights([{ km: 50 }, { km: 100 }, { km: 0 }]), [0.5, 1, 0]);
	assert.deepEqual(monthHeights([{ km: 0 }]), [0]);
});

test('monthRange: 달 범위', () => {
	assert.deepEqual(monthRange('2026-09'), { from: '2026-09-01', to: '2026-09-30' });
	assert.equal(monthRange('2024-02').to, '2024-02-29');
	assert.equal(monthRange('2026-12').to, '2026-12-31');
});
