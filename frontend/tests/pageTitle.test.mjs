import test from 'node:test';
import assert from 'node:assert/strict';
import { pageTitle } from '../src/lib/a11y/pageTitle.ts';

test('pageTitle: 부분을 · 로 잇고 RunPulse 를 붙인다', () => {
	assert.equal(pageTitle('Coach'), 'Coach · RunPulse');
	assert.equal(pageTitle('A', 'B'), 'A · B · RunPulse');
});
test('pageTitle: 빈 값은 버리고 전부 비면 RunPulse', () => {
	assert.equal(pageTitle('', null, undefined, '  '), 'RunPulse');
	assert.equal(pageTitle(null, 'X'), 'X · RunPulse');
});
