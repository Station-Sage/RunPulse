import { test } from 'node:test';
import assert from 'node:assert/strict';
import { finderQuery, shortDate, heatCellLabel, moveHeatCell, isMonthInProgress, QUICK_CHIPS } from '../src/lib/libraryHome.ts';

test('finderQuery: 공백 제거·인코딩, 빈 값은 null', () => {
	assert.equal(finderQuery('  '), null);
	assert.equal(finderQuery(' 한강 10k '), 'q=%ED%95%9C%EA%B0%95%2010k');
});

test('shortDate 요일', () => {
	assert.equal(shortDate('2026-09-20'), '9/20(일)');
	assert.equal(shortDate('2026-01-05'), '1/5(월)');
});

test('heatCellLabel: 거리/쉰 날', () => {
	assert.equal(heatCellLabel('2026-09-20', 24.24), '9/20(일) · 24.2km');
	assert.equal(heatCellLabel('2026-09-21', 0), '9/21(월) · 쉰 날');
});

test('moveHeatCell: 화살표 이동·경계', () => {
	const cells = [
		{ col: 0, row: 0 }, { col: 0, row: 1 },
		{ col: 1, row: 0 }, { col: 1, row: 1 }
	];
	assert.equal(moveHeatCell(cells, 0, 'ArrowRight'), 2);
	assert.equal(moveHeatCell(cells, 0, 'ArrowDown'), 1);
	assert.equal(moveHeatCell(cells, 0, 'ArrowLeft'), 0);
	assert.equal(moveHeatCell(cells, 0, 'ArrowUp'), 0);
	assert.equal(moveHeatCell(cells, 0, 'x'), 0);
});

test('isMonthInProgress', () => {
	assert.equal(isMonthInProgress('2026-10', '2026-10-05'), true);
	assert.equal(isMonthInProgress('2026-09', '2026-10-05'), false);
});

test('빠른 칩에 대회 포함', () => {
	assert.ok(QUICK_CHIPS.some((c) => c.query === 'type=race'));
});
