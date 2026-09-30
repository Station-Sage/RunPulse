import { test } from 'node:test';
import assert from 'node:assert/strict';
import { splitVisible, chipLabel, chipTarget, driftText, snapshotLine } from '../src/lib/answerEvidence.ts';

const ev = (metric, extra = {}) => ({ type: 'metric', metric, value: 1, label: metric, role: 'supports', drill: { scope_type: 'daily', scope_id: 'd' }, ...extra });

test('splitVisible: 3개까지 노출, pinned는 항상 노출', () => {
	const items = [ev('a'), ev('b'), ev('c'), ev('d'), ev('checkin', { pinned: true, type: 'user_input', drill: null })];
	const { visible, hidden } = splitVisible(items);
	assert.deepEqual(visible.map((i) => i.metric), ['a', 'b', 'checkin']);
	assert.deepEqual(hidden.map((i) => i.metric), ['c', 'd']);
	assert.equal(splitVisible([ev('a')]).hidden.length, 0);
	assert.equal(splitVisible([]).visible.length, 0);
});

test('chipLabel: 투영은 단정하지 않는 문구', () => {
	assert.equal(chipLabel(ev('race_form_projection', { value: 25.3 })), '계획대로 가면 레이스 아침 폼 약 +25');
	assert.equal(chipLabel(ev('race_form_projection', { value: -3.26 })), '계획대로 가면 레이스 아침 폼 약 −3.3');
	assert.equal(chipLabel(ev('tsb', { label: 'TSB -11' })), 'TSB -11');
});

test('chipTarget: legacy·drill 없음은 none, 투영은 race', () => {
	assert.equal(chipTarget(ev('tsb')), 'drill');
	assert.equal(chipTarget(ev('tsb', { role: 'legacy' })), 'none');
	assert.equal(chipTarget(ev('body_battery', { drill: null })), 'none');
	assert.equal(chipTarget(ev('race_form_projection', { drill: null })), 'race');
});

test('driftText: 변한 근거만, 없으면 null', () => {
	assert.equal(driftText(undefined), null);
	assert.equal(driftText([ev('tsb')]), null);
	const d = ev('tsb', { drifted: true, status_label: 'TSB', snapshot: { value: -10.7 }, current: { display: '−3.3' } });
	assert.equal(driftText([d]), '답변 이후 데이터가 바뀌었어요 · TSB −10.7 → −3.3');
});

test('snapshotLine: 같으면 한 줄, 다르면 화살표', () => {
	const snap = { value: -10.7, computed_at: '2026-09-25 10:51:00', version: 'pmc_v1', as_of: 'x' };
	assert.deepEqual(snapshotLine(ev('tsb', { snapshot: snap })), { text: '답변 당시 −10.7 (9/25 10:51 계산 · pmc_v1)', changed: false });
	const cur = { display: '−3.3', value: -3.3, computed_at: '2026-09-27 11:57:00', version: 'pmc_v1' };
	assert.deepEqual(snapshotLine(ev('tsb', { snapshot: snap, current: cur, drifted: true })), {
		text: '답변 당시 −10.7 (9/25 10:51 계산 · pmc_v1) → 현재 −3.3 (9/27 11:57 재계산 · pmc_v1)',
		changed: true
	});
	assert.equal(snapshotLine(ev('tsb')), null);
});
