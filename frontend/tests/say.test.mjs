import test from 'node:test';
import assert from 'node:assert/strict';
import { say } from '../src/lib/a11y/say.ts';
import { subscribeAnnounce } from '../src/lib/a11y/announce.ts';

test('마운트 시 발신, 문구가 바뀔 때만 update 에서 발신', () => {
	const got = [];
	const off = subscribeAnnounce((l, t) => got.push([l, t]));
	const a = say({}, { text: 'say-A', level: 'assertive' });
	a.update({ text: 'say-A', level: 'assertive' });
	a.update({ text: 'say-B' });
	off();
	assert.deepEqual(got, [['assertive', 'say-A'], ['polite', 'say-B']]);
});
