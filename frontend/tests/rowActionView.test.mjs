import test from 'node:test';
import assert from 'node:assert/strict';
import {
	rowActionMode, opAvailability, reducePreview, weekPreview, toastText, actionErrorText, userAdjustmentSummary
} from '../src/lib/rowActionView.ts';
class ApiError extends Error { constructor(status, body) { super(body.error?.message ?? ''); this.status = status; this.details = body.error?.details; } }

const w = (o = {}) => ({ id: 1, date: '2026-10-09', workout_type: 'easy', distance_km: 10, completed: 0, ...o });

test('mode: hidden/locked/active', () => {
	const T = '2026-10-09';
	assert.equal(rowActionMode(w(), T), 'active');
	assert.equal(rowActionMode(w({ date: '2026-10-10' }), T), 'locked');
	assert.equal(rowActionMode(w({ date: '2026-10-08' }), T), 'hidden');
	assert.equal(rowActionMode(w({ completed: 1 }), T), 'hidden');
	assert.equal(rowActionMode(w({ superseded: true }), T), 'hidden');
	assert.equal(rowActionMode(w({ workout_type: 'rest' }), T), 'hidden');
	assert.equal(rowActionMode(w({ workout_type: 'rest', adjusted: true }), T), 'active');
});

test('availability: quality and short sessions block reduce', () => {
	assert.equal(opAvailability(w()).reduce.ok, true);
	assert.equal(opAvailability(w({ workout_type: 'interval' })).reduce.ok, false);
	assert.equal(opAvailability(w({ distance_km: 3.5 })).reduce.ok, false);
	assert.equal(opAvailability(w({ workout_type: 'interval' })).rest.ok, true);
});

test('reducePreview: cap and floor', () => {
	assert.deepEqual(reducePreview(10, 20), { km: 8, valid: true, hint: null });
	assert.equal(reducePreview(10, 60).valid, false);
	assert.equal(reducePreview(5, 50).valid, false);
});

test('weekPreview and toast text', () => {
	assert.deepEqual(weekPreview(57.8, 2), { before: 57.8, after: 55.8 });
	const res = { adjustment: { after: { distance_km: 8 } }, compliance: null, week_planned_km: { before: 57.8, after: 55.8 } };
	assert.equal(toastText('reduce', res), '오늘 8km로 줄였어요 · 이번 주 57.8→55.8km');
	assert.match(toastText('rest', res), /^오늘은 쉬어요/);
	assert.match(toastText('skip', res), /건너뛰었어요/);
});

test('error text', () => {
	assert.match(actionErrorText(new ApiError(409, { error: { code: 'CONFLICT', details: { reason: 'LOCKED' } } })), /오늘 세션만/);
	assert.match(actionErrorText(new ApiError(404, {})), /찾을 수 없어요/);
	assert.match(actionErrorText(new Error('x')), /처리하지 못했어요/);
});

test('userAdjustmentSummary ignores crs', () => {
	const base = w({ adjusted: true, original: { workout_type: 'easy', distance_km: 10 } });
	assert.equal(userAdjustmentSummary({ ...base, adjustment: { id: 1, source: 'crs', op: 'replace' } }, (t) => t), null);
	assert.deepEqual(userAdjustmentSummary({ ...base, adjustment: { id: 1, source: 'user', op: 'reduce' } }, (t) => t),
		{ badge: '직접 조정', original: '원래 easy 10km' });
});

test('moveCandidates: 내일부터 3일, 같은 주만', async () => {
	const { moveCandidates } = await import('../src/lib/rowActionView.ts');
	assert.deepEqual(moveCandidates('2026-10-07').map((d) => d.date), ['2026-10-08', '2026-10-09', '2026-10-10']);
	assert.deepEqual(moveCandidates('2026-10-10').map((d) => d.date), ['2026-10-11']);
	assert.deepEqual(moveCandidates('2026-10-11'), []);
	assert.equal(opAvailability(w({ workout_type: 'race' })).move.ok, false);
	assert.match(actionErrorText(new ApiError(409, { error: { details: { reason: 'TARGET_HARD' } } })), /강한 훈련/);
});

test('Q 세션: 인터벌은 반복 횟수, 강도는 정해진 비율, 이지로 바꾸기', async () => {
	const { reduceInput } = await import('../src/lib/rowActionView.ts');
	const iv = w({ workout_type: 'interval', distance_km: 10, interval_prescription: JSON.stringify({ sets: 6, rep_m: 1000 }) });
	assert.deepEqual(reduceInput(iv), { kind: 'reps', options: [1, 2], free: false });
	assert.equal(opAvailability(iv).reduce.ok, true);
	assert.deepEqual(reduceInput({ ...iv, interval_prescription: JSON.stringify({ sets: 3 }) }).options, [1]);
	assert.deepEqual(reduceInput(w({ workout_type: 'tempo', distance_km: 8 })).options, [20, 30]);
	assert.deepEqual(reduceInput(w({ workout_type: 'tempo', distance_km: 2.2 })).options, []);
	assert.equal(opAvailability(w({ workout_type: 'tempo' })).easy.ok, true);
	assert.equal(opAvailability(w()).easy.ok, false);
});
