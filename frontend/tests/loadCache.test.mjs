// 02-performance.md P-5 — swrLoad(stale-while-revalidate) 순수 로직 테스트.
import test from 'node:test';
import assert from 'node:assert/strict';
import { swrLoad, _clearSwrCacheForTest } from '../src/lib/loadCache.ts';

test('swrLoad — 캐시 없으면 fetcher를 기다려 결과를 반환하고 캐시에 저장', async () => {
	_clearSwrCacheForTest();
	let calls = 0;
	const result = await swrLoad('k1', async () => { calls++; return 'v1'; }, () => {});
	assert.equal(result, 'v1');
	assert.equal(calls, 1);
});

test('swrLoad — staleMs 이내 재방문은 네트워크 없이 캐시를 즉시 반환', async () => {
	_clearSwrCacheForTest();
	let calls = 0;
	await swrLoad('k2', async () => { calls++; return 'first'; }, () => {}, 10_000);
	const second = await swrLoad('k2', async () => { calls++; return 'second'; }, () => {}, 10_000);
	assert.equal(second, 'first');
	assert.equal(calls, 1, '두 번째 호출은 fetcher를 부르지 않아야 함');
});

test('swrLoad — staleMs 지난 뒤 재방문은 캐시를 즉시 반환하면서 백그라운드로 갱신 후 invalidate 호출', async () => {
	_clearSwrCacheForTest();
	await swrLoad('k3', async () => 'first', () => {}, 0);

	let invalidatedWith = null;
	const bgDone = new Promise((resolve) => {
		var second = swrLoad(
			'k3',
			async () => 'fresh',
			(key) => { invalidatedWith = key; resolve(); },
			0
		);
		second.then((v) => assert.equal(v, 'first', '갱신 중에도 즉시 반환되는 값은 이전 캐시'));
	});
	await bgDone;
	assert.equal(invalidatedWith, 'k3');

	// 갱신이 끝난 뒤엔 캐시가 새 값으로 교체돼 있어야 함(staleMs=0이라 바로 다음 호출도 백그라운드 갱신을 또 트리거하지만,
	// 반환값 자체는 이미 교체된 'fresh'여야 한다).
	const third = await swrLoad('k3', async () => 'fresh', () => {}, 100_000);
	assert.equal(third, 'fresh');
});

test('swrLoad — 백그라운드 갱신이 실패해도 이전 캐시는 그대로 유지', async () => {
	_clearSwrCacheForTest();
	await swrLoad('k4', async () => 'ok', () => {}, 0);

	let invalidateCalled = false;
	await new Promise((resolve) => {
		swrLoad(
			'k4',
			async () => { throw new Error('network down'); },
			() => { invalidateCalled = true; },
			0
		).then(() => setTimeout(resolve, 10));
	});
	assert.equal(invalidateCalled, false, '실패 시 invalidate는 호출되지 않아야 함');

	const after = await swrLoad('k4', async () => 'ok', () => {}, 100_000);
	assert.equal(after, 'ok', '실패 후에도 이전 캐시가 남아 있어야 함');
});
