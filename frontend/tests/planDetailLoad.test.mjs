// P-25 — 플랜 상세 스트리밍 로더: 플랜만 기다리고 보조 데이터는 거부되지 않는 약속으로 넘긴다.
import test from 'node:test';
import assert from 'node:assert/strict';
import { ApiError } from '../src/lib/api/client.ts';
import { loadPlanDetail } from '../src/lib/planDetailLoad.ts';

const never = () => new Promise(() => {});
const err = (status, code) => new ApiError(status, { error: { code, message: 'm' } });
const PLAN = { goal: { id: 3, name: 'g' }, workouts: [] };

function api(over = {}) {
	const calls = [];
	const base = {
		getActivePlan: (id) => (calls.push(['plan', id]), Promise.resolve(PLAN)),
		getTodaysAdjustment: () => (calls.push(['adj']), never()),
		getPlanAdaptation: () => (calls.push(['adapt']), never()),
		getReplanLast: () => (calls.push(['replan']), never()),
		getPlanWeeks: (id) => (calls.push(['weeks', id]), never())
	};
	return { api: { ...base, ...over }, calls };
}

test('플랜만 기다린다 — 보조 요청이 끝나지 않아도 로더는 끝나고 5개 요청은 모두 시작됨', async () => {
	const { api: a, calls } = api();
	const d = await loadPlanDetail('3', a);
	assert.equal(d.plan, PLAN);
	assert.equal(d.errorMessage, null);
	assert.equal(d.planFailure, null);
	for (const k of ['adjustment', 'adaptation', 'replanEntry', 'weeks']) assert.ok(d[k] instanceof Promise, k);
	assert.deepEqual(calls.map((c) => c[0]).sort(), ['adapt', 'adj', 'plan', 'replan', 'weeks']);
	assert.deepEqual(calls.find((c) => c[0] === 'weeks'), ['weeks', 3]);
});

test('보조 데이터 실패는 거부되지 않고 분류된 결과·null 로 끝난다', async () => {
	const { api: a } = api({
		getTodaysAdjustment: () => Promise.reject(err(500, 'X')),
		getPlanAdaptation: () => Promise.reject(err(0, 'NETWORK')),
		getReplanLast: () => Promise.reject(err(500, 'X')),
		getPlanWeeks: () => Promise.reject(err(500, 'X'))
	});
	const orig = console.error;
	console.error = () => {};
	try {
		const d = await loadPlanDetail('3', a);
		assert.equal(await d.adjustment, null);
		assert.equal(await d.replanEntry, null);
		const ad = await d.adaptation;
		assert.equal(ad.ok, false);
		assert.equal(ad.failure.kind, 'network');
		const w = await d.weeks;
		assert.equal(w.ok, false);
		assert.equal(w.failure.kind, 'server');
	} finally {
		console.error = orig;
	}
});

test('보조 데이터 성공 — replanEntry 는 entry 만, weeks 는 ok 결과', async () => {
	const entry = { eligible: true, reason: null, last: null };
	const { api: a } = api({
		getTodaysAdjustment: () => Promise.resolve({ adjusted: false }),
		getPlanAdaptation: () => Promise.resolve({ acwr: null }),
		getReplanLast: () => Promise.resolve({ last: null, entry }),
		getPlanWeeks: () => Promise.resolve({ weeks: [] })
	});
	const d = await loadPlanDetail('3', a);
	assert.deepEqual(await d.adjustment, { adjusted: false });
	assert.equal(await d.replanEntry, entry);
	assert.deepEqual(await d.weeks, { ok: true, data: { weeks: [] } });
	assert.deepEqual(await d.adaptation, { ok: true, data: { acwr: null } });
});

test('플랜 실패 — 실패 분류를 넘기고 보조 영역은 null', async () => {
	const { api: a } = api({ getActivePlan: () => Promise.reject(err(404, 'NOT_FOUND')) });
	const d = await loadPlanDetail('3', a);
	assert.equal(d.plan, null);
	assert.equal(d.errorMessage, '플랜을 불러올 수 없습니다.');
	assert.equal(d.planFailure.kind, 'not_found');
	assert.equal(await d.weeks, null);
	assert.equal(await d.adjustment, null);
});

test('잘못된 id — 요청 없이 오류 문구', async () => {
	const { api: a, calls } = api();
	const d = await loadPlanDetail('abc', a);
	assert.equal(d.errorMessage, '잘못된 플랜 ID입니다.');
	assert.equal(d.planFailure, null);
	assert.equal(calls.length, 0);
	assert.equal(await d.adaptation, null);
});
