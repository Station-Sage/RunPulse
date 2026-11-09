import { test } from 'node:test';
import assert from 'node:assert/strict';
import { candidateHint, nextEffort } from '../src/lib/raceConfirm.ts';

test('nextEffort — 같은 버튼 재탭은 해제하지 않음 (T-13)', () => {
	assert.equal(nextEffort('fun', 'fun'), undefined);
	assert.equal(nextEffort(null, 'fun'), 'fun');
	assert.equal(nextEffort('fun', 'allout'), 'allout');
	assert.equal(nextEffort('fun', null), null);
	assert.equal(nextEffort(null, null), undefined);
});

test('candidateHint (T-14)', () => {
	assert.equal(candidateHint({ why: 'name', distance_mismatch: false }), null);
	assert.match(candidateHint({ why: 'event_type', distance_mismatch: false }), /기기에서 대회로/);
	assert.match(candidateHint({ why: 'name', distance_mismatch: true }), /거리가 달라요/);
});
