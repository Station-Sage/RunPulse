import test from 'node:test';
import assert from 'node:assert/strict';
import {
	adjustmentActions,
	adjustmentDelta,
	adjustmentHeadline,
	adjustmentStateText
} from '../src/lib/adjustmentView.ts';

const side = (t, km) => ({ workout_type: t, distance_km: km, target_pace_min: null, target_pace_max: null, description: null });
const adj = (b, a) => ({ id: 1, goal_id: 1, workout_id: 1, date: 'd', op: 'x', before: b, after: a, reasons: [], decision: 'proposed', rev: 1, state: 'proposed' });
const label = (t) => ({ tempo: '템포', easy: '이지', rest: '휴식' })[t] ?? t;

test('adjustmentActions: 상태별 버튼', () => {
	assert.equal(adjustmentActions('proposed'), 'decide');
	assert.equal(adjustmentActions('accepted'), 'undo');
	for (const s of ['declined', 'undone', 'expired', 'stale', 'none', 'future', undefined]) assert.equal(adjustmentActions(s), 'none');
});

test('adjustmentStateText / headline', () => {
	assert.match(adjustmentStateText('stale'), /적용되지 않아요/);
	assert.equal(adjustmentStateText('proposed'), null);
	assert.equal(adjustmentHeadline('accepted'), '조정 적용됨');
	assert.equal(adjustmentHeadline('declined'), null);
});

test('adjustmentDelta: 유형·거리 변화', () => {
	assert.equal(adjustmentDelta(adj(side('tempo', 10), side('easy', 10)), label), '템포 → 이지');
	assert.equal(adjustmentDelta(adj(side('tempo', 10), side('rest', null)), label), '템포 → 휴식 (10km → -)');
	assert.equal(adjustmentDelta(adj(side('easy', 8), side('easy', 6)), label), '이지 (8km → 6km)');
});
