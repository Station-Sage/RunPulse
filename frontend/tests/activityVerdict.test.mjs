import { test } from 'node:test';
import assert from 'node:assert/strict';
import { verdictDrillSlug, pickVerdictEvidence } from '../src/lib/activityVerdict.ts';

test('verdictDrillSlug: m. 접두 제거, info는 null', () => {
	assert.equal(verdictDrillSlug({ kind: 'drill', label: '날씨 보정', target: 'm.fearp' }), 'fearp');
	assert.equal(verdictDrillSlug({ kind: 'info', label: '최대심박 80%', target: 'hr_pct_max' }), null);
	assert.equal(verdictDrillSlug({ kind: 'drill', label: 'x' }), null);
});

test('pickVerdictEvidence: 최대 3개, 드릴 우선, 순서 유지', () => {
	const ev = [
		{ kind: 'info', label: 'a' },
		{ kind: 'info', label: 'b' },
		{ kind: 'info', label: 'c' },
		{ kind: 'drill', label: 'd', target: 'm.fearp' },
	];
	assert.deepEqual(pickVerdictEvidence(ev).map((e) => e.label), ['a', 'b', 'd']);
	assert.deepEqual(pickVerdictEvidence([]), []);
});
