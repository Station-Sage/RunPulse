// ADR-057 — 마일스톤 전체 이력의 월별 묶음·필터 칩·날짜·아이콘/라벨.
import test from 'node:test';
import assert from 'node:assert/strict';
import { dayLabel, filterChips, groupByMonth, parseTypeParam } from '../src/lib/milestoneHistory.ts';
import { MILESTONE_LABEL, milestoneIconName, milestoneLabel } from '../src/lib/milestoneIcon.ts';

test('groupByMonth: 최신순 유지, 월 경계에서 나눈다', () => {
	const g = groupByMonth([{ date: '2026-11-19' }, { date: '2026-11-02' }, { date: '2026-10-31' }, { date: '2025-12-01' }]);
	assert.deepEqual(g.map((x) => [x.label, x.items.length]), [['2026년 11월', 2], ['2026년 10월', 1], ['2025년 12월', 1]]);
	assert.deepEqual(groupByMonth([]), []);
});

test('dayLabel', () => {
	assert.equal(dayLabel('2026-03-05'), '3월 5일');
});

test('filterChips: 기록 있는 종류만, 정해진 순서, 건수 표시', () => {
	const c = filterChips([{ type: 'goal_set', count: 2 }, { type: 'pb', count: 1 }, { type: 'zzz', count: 1 }, { type: 'recovery', count: 0 }]);
	assert.deepEqual(c.map((x) => x.value), ['pb', 'goal_set', 'zzz']);
	assert.equal(c[0].label, '개인 최고 1');
	assert.equal(c[2].label, '기록 1');
});

test('parseTypeParam: 형식 밖은 전체', () => {
	assert.equal(parseTypeParam('race_finish'), 'race_finish');
	assert.equal(parseTypeParam('Bad!'), null);
	assert.equal(parseTypeParam(null), null);
});

test('모든 표시 종류에 아이콘·한국어 라벨이 있다(metric_recompute 제외)', () => {
	const types = Object.keys(MILESTONE_LABEL);
	assert.equal(types.length, 12);
	assert.ok(!types.includes('metric_recompute'));
	for (const t of types.filter((x) => x !== 'goal_changed')) assert.notEqual(milestoneIconName(t), 'note', t);
	assert.equal(milestoneIconName('race_finish'), 'medal');
	assert.equal(milestoneIconName('unknown'), 'note');
	assert.equal(milestoneLabel('injury_start'), '부상');
});
