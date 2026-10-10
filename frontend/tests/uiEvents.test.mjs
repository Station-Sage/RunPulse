import test from 'node:test';
import assert from 'node:assert/strict';
import { rollbackToV1, ROLLBACK_REASONS } from '../src/lib/rollback.ts';

test('four reasons offered', () => assert.equal(ROLLBACK_REASONS.length, 4));

test('rollback sends trimmed event + preference then navigates', async () => {
	const sent = [];
	let nav = '', pref = 0;
	await rollbackToV1('hard_to_use', ' 메모 ', {
		sendEvent: async (b) => sent.push(b),
		setV1: async () => pref++,
		navigate: (u) => (nav = u)
	});
	assert.equal(nav, '/dashboard');
	assert.equal(pref, 1);
	assert.deepEqual(sent[0], { kind: 'v1_rollback', reason: 'hard_to_use', reason_note: '메모' });
});

test('skip sends null reason without note', async () => {
	const sent = [];
	await rollbackToV1(null, '  ', { sendEvent: async (b) => sent.push(b), setV1: async () => {}, navigate: () => {} });
	assert.deepEqual(sent[0], { kind: 'v1_rollback', reason: null });
});

test('navigates even if the server hangs or rejects', async () => {
	let nav = 0;
	await rollbackToV1(null, '', { sendEvent: () => new Promise(() => {}), setV1: async () => { throw new Error('x'); }, navigate: () => nav++, timeoutMs: 30 });
	assert.equal(nav, 1);
});
