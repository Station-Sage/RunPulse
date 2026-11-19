import { test } from 'node:test';
import assert from 'node:assert/strict';
import { AI_MARK_LABEL, aiMarkText, isAiWorded } from '../src/lib/aiWording.ts';

test('isAiWorded: source==="ai" 만 참', () => {
	assert.equal(isAiWorded({ source: 'ai' }), true);
	assert.equal(isAiWorded('ai'), true);
	assert.equal(isAiWorded({ source: 'rule' }), false);
	assert.equal(isAiWorded(null), false);
	assert.equal(isAiWorded({}), false);
});

test('aiMarkText: 접두 점 옵션', () => {
	assert.equal(aiMarkText(), AI_MARK_LABEL);
	assert.equal(aiMarkText(true), '· AI 해설');
});
