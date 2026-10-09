import test from 'node:test';
import assert from 'node:assert/strict';
import {
	rowActionMode, opAvailability, reducePreview, weekPreview, toastText, actionErrorText, userAdjustmentSummary, rowSheetParam
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

test('loadDeltaView: 0.5% 미만이면 숨기고, ACWR 경계를 넘을 때만 warn', async () => {
	const { loadDeltaView } = await import('../src/lib/rowActionView.ts');
	const d = { week_pct: -15.2, acwr_before: 1.05, acwr_after: 0.92, week_load_before: 500, week_load_after: 424 };
	assert.deepEqual(loadDeltaView(d), { text: '이번 주 부하 −15% · ACWR 1.05 → 0.92', tone: 'none' });
	assert.equal(loadDeltaView({ ...d, acwr_after: 0.75 }).tone, 'warn');
	assert.equal(loadDeltaView({ ...d, week_pct: 0.2 }), null);
	assert.equal(loadDeltaView(null), null);
	assert.equal(loadDeltaView({ ...d, acwr_before: null }).text, '이번 주 부하 −15%');
});

test('통증: 정도별 허용 op·기본 op, 부위 최대 3곳', async () => {
	const { painOps, togglePainSite, painReady, REASONS } = await import('../src/lib/rowActionView.ts');
	assert.ok(REASONS.some((r) => r.key === 'pain'));
	assert.deepEqual(painOps('moderate', 'easy'), { allowed: ['rest'], default: 'rest' });
	assert.equal(painOps('severe', 'long').default, 'rest');
	assert.equal(painOps('mild', 'tempo').default, 'easy');
	assert.equal(painOps('mild', 'easy').default, null);
	assert.ok(!painOps('mild', 'easy').allowed.includes('move'));
	assert.deepEqual(painOps(undefined, 'easy').allowed, []);
	let s = [];
	for (const k of ['knee', 'foot', 'hip', 'calf']) s = togglePainSite(s, k);
	assert.deepEqual(s, ['knee', 'foot', 'hip']);
	assert.deepEqual(togglePainSite(s, 'foot'), ['knee', 'hip']);
	assert.ok(painReady('mild', ['knee']) && !painReady('mild', []) && !painReady(undefined, ['knee']));
});

test('rowSheetParam: 시트 딥링크 값', () => {
	assert.equal(rowSheetParam(42), 'row-42');
});
