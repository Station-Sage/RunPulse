// P-25 — 보조 데이터 약속 → 화면 상태(같은 화면 다시 읽기는 이전 값 유지, 다른 화면은 초기화, 마지막 약속만 반영).
import test from 'node:test';
import assert from 'node:assert/strict';
import { createStreamFollower } from '../src/lib/streamed.ts';

function deferred() {
	let resolve, reject;
	const p = new Promise((res, rej) => ((resolve = res), (reject = rej)));
	return { p, resolve, reject };
}
const tick = () => new Promise((r) => setTimeout(r, 0));

test('첫 약속: 대기(undefined,false) → 끝나면 값', async () => {
	const log = [];
	const f = createStreamFollower((v, ready) => log.push([v, ready]));
	const d = deferred();
	f('3', d.p);
	assert.deepEqual(log, [[undefined, false]]);
	d.resolve('A');
	await tick();
	assert.deepEqual(log.at(-1), ['A', true]);
});

test('같은 key 다시 읽기는 이전 값을 지우지 않는다', async () => {
	const log = [];
	const f = createStreamFollower((v, ready) => log.push([v, ready]));
	f('3', Promise.resolve('A'));
	await tick();
	const n = log.length;
	const d = deferred();
	f('3', d.p);
	assert.equal(log.length, n);
	d.resolve('B');
	await tick();
	assert.deepEqual(log.at(-1), ['B', true]);
});

test('다른 key 면 바로 초기화, 늦게 끝난 옛 약속은 무시', async () => {
	const log = [];
	const f = createStreamFollower((v, ready) => log.push([v, ready]));
	const old = deferred();
	f('3', old.p);
	const next = deferred();
	f('4', next.p);
	assert.deepEqual(log.at(-1), [undefined, false]);
	next.resolve('N');
	await tick();
	old.resolve('O');
	await tick();
	assert.deepEqual(log.at(-1), ['N', true]);
	assert.ok(!log.some(([v]) => v === 'O'));
});

test('거부되면 undefined 로 끝난다(대기 상태로 남지 않음)', async () => {
	const log = [];
	const f = createStreamFollower((v, ready) => log.push([v, ready]));
	f('3', Promise.reject(new Error('x')));
	await tick();
	assert.deepEqual(log.at(-1), [undefined, true]);
});
