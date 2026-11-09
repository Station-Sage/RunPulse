import test from 'node:test';
import assert from 'node:assert/strict';
import { classifyRequest, snapshotKey, demoResponse } from '../src/lib/demoMode.ts';

test('API가 아니면 통과', () => {
	assert.equal(classifyRequest('GET', '/v2/_app/x.js').kind, 'pass');
});
test('GET은 스냅샷 키(쿼리 정렬)', () => {
	assert.deepEqual(classifyRequest('GET', '/api/v1/library/activities?b=2&a=1'), { kind: 'read', key: '/library/activities?a=1&b=2' });
	assert.equal(snapshotKey('/api/v1/today'), '/today');
});
test('쓰기 메서드는 모두 차단', () => {
	for (const m of ['POST', 'PUT', 'PATCH', 'DELETE']) assert.equal(classifyRequest(m, '/api/v1/today/checkin').kind, 'blocked');
});
test('응답: 적중 200, 미적중 404, 차단 403, 통과 null', async () => {
	const snap = { '/today': { data: { ok: 1 } } };
	assert.equal(demoResponse({ kind: 'read', key: '/today' }, snap).status, 200);
	assert.equal(demoResponse({ kind: 'read', key: '/nope' }, snap).status, 404);
	const r = demoResponse({ kind: 'blocked' }, snap);
	assert.equal(r.status, 403);
	assert.equal((await r.json()).error.code, 'DEMO_READONLY');
	assert.equal(demoResponse({ kind: 'pass' }, snap), null);
});
test('E-22: /api/v1 밖 서버 경로·다른 출처는 실서버로 보내지 않는다', async () => {
	const o = 'http://localhost';
	assert.equal(classifyRequest('GET', '/auth/session', o).kind, 'unavailable');
	assert.equal(classifyRequest('GET', '/api/garmin/x', o).kind, 'unavailable');
	assert.equal(classifyRequest('POST', '/api/garmin/local-sync', o).kind, 'blocked');
	assert.equal(classifyRequest('POST', '/auth/logout', o).kind, 'blocked');
	assert.equal(classifyRequest('GET', 'https://evil.example/x', o).kind, 'unavailable');
	assert.equal(classifyRequest('GET', 'http://localhost/v2/demo/snapshot.json', o).kind, 'pass');
	assert.equal(classifyRequest('GET', 'http://localhost/api/v1/today', o).kind, 'read');
	assert.equal(classifyRequest('GET', '/api/v1x/today', o).kind, 'unavailable');
	const r = demoResponse({ kind: 'unavailable' }, {});
	assert.equal(r.status, 404);
	assert.equal((await r.json()).error.code, 'DEMO_NOT_AVAILABLE');
});
