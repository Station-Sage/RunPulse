// lib/connectivity.ts — 오프라인 배너 단계·문구 (E-17). 실행: npm run test:unit
import test from 'node:test';
import assert from 'node:assert/strict';
import { connectivityText, watchConnectivity } from '../src/lib/connectivity.ts';

test('connectivityText: 평상시 null, 오프라인·복구는 해요체 문구', () => {
	assert.equal(connectivityText('online'), null);
	assert.match(connectivityText('offline'), /끊겼어요/);
	assert.match(connectivityText('restored'), /연결됐어요/);
});

test('watchConnectivity: 시작 시 오프라인이면 즉시 알리고, 복구 후 online 으로 돌아간다', async () => {
	const target = new EventTarget();
	const seen = [];
	const stop = watchConnectivity(target, () => false, (p) => seen.push(p), 10);
	assert.deepEqual(seen, ['offline']);
	target.dispatchEvent(new Event('online'));
	assert.deepEqual(seen, ['offline', 'restored']);
	await new Promise((r) => setTimeout(r, 30));
	assert.deepEqual(seen, ['offline', 'restored', 'online']);
	stop();
	target.dispatchEvent(new Event('offline'));
	assert.equal(seen.length, 3);
});
