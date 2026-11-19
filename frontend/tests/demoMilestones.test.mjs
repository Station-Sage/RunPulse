import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { demoMilestoneResponse, pageHistory, MILESTONE_BASE_KEY } from '../src/lib/demoMilestones.ts';
import { classifyRequest, demoResponse } from '../src/lib/demoMode.ts';

const e = (id, type, date) => ({ id, type, date, title: `${type} ${id}`, detail: null, activity_id: null });
const all = {
	items: [e(5, 'pb', '2026-10-05'), e(4, 'goal_set', '2026-10-05'), e(3, 'pb', '2026-09-01'), e(2, 'longest_run', '2026-08-01'), e(1, 'pb', '2026-07-01')],
	next_before: null,
	type_counts: [{ type: 'pb', count: 3 }, { type: 'goal_set', count: 1 }, { type: 'longest_run', count: 1 }]
};
const snap = { [MILESTONE_BASE_KEY]: { data: all } };
const page = (qs) => pageHistory(all, new URLSearchParams(qs));

test('기본 50건·최신순(date desc, id desc), 다음 커서 없음', () => {
	const r = page('');
	assert.equal(r.status, 200);
	assert.deepEqual(r.body.data.items.map((m) => m.id), [5, 4, 3, 2, 1]);
	assert.equal(r.body.data.next_before, null);
});
test('limit 으로 자르고 next_before 로 이어 받는다(같은 날짜는 id 로 구분)', () => {
	const p1 = page('limit=1');
	assert.deepEqual(p1.body.data.items.map((m) => m.id), [5]);
	assert.equal(p1.body.data.next_before, '2026-10-05:5');
	const p2 = page(`limit=2&before=${p1.body.data.next_before}`);
	assert.deepEqual(p2.body.data.items.map((m) => m.id), [4, 3]);
	const p3 = page(`limit=2&before=${p2.body.data.next_before}`);
	assert.deepEqual(p3.body.data.items.map((m) => m.id), [2, 1]);
	assert.equal(p3.body.data.next_before, null);
});
test('종류 필터 — 칩 집계(type_counts)는 필터와 무관하게 전체', () => {
	const r = page('type=pb&limit=2');
	assert.deepEqual(r.body.data.items.map((m) => m.id), [5, 3]);
	assert.equal(r.body.data.next_before, '2026-09-01:3');
	assert.deepEqual(r.body.data.type_counts, all.type_counts);
	assert.deepEqual(page('type=goal_set,longest_run').body.data.items.map((m) => m.id), [4, 2]);
});
test('형식 오류는 서버처럼 400 INVALID_PARAM', () => {
	for (const qs of ['type=PB', 'before=2026-10-05', 'limit=0', 'limit=101', 'limit=x']) {
		const r = page(qs);
		assert.equal(r.status, 400, qs);
		assert.equal(r.body.error.code, 'INVALID_PARAM');
	}
});
test('demoResponse: 정확한 키가 없어도 마일스톤 요청은 스냅샷 전체 이력에서 만든다', async () => {
	const d = classifyRequest('GET', '/api/v1/library/milestones?type=pb&limit=50', 'http://localhost');
	const r = demoResponse(d, snap);
	assert.equal(r.status, 200);
	assert.equal((await r.json()).data.items.length, 3);
	const t = demoResponse(classifyRequest('GET', '/api/v1/today/milestones?limit=2', 'http://localhost'), snap);
	assert.deepEqual((await t.json()).data.milestones.map((m) => m.id), [5, 4]);
	assert.equal(demoMilestoneResponse('/today', snap), null);
	assert.equal(demoResponse({ kind: 'read', key: '/library/milestones?limit=50' }, {}).status, 404);
});
test('배포 스냅샷에 전체 이력이 있고 여러 종류(칩)를 보여 줄 수 있다', () => {
	const s = JSON.parse(readFileSync(new URL('../static/demo/snapshot.json', import.meta.url), 'utf-8'));
	const r = demoMilestoneResponse('/library/milestones?limit=50', s);
	assert.equal(r.status, 200);
	assert.ok(r.body.data.items.length >= 5);
	assert.ok(r.body.data.type_counts.length > 1);
	assert.ok(!r.body.data.items.some((m) => m.type === 'metric_recompute'));
});
