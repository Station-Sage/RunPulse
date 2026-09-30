import { test } from 'node:test';
import assert from 'node:assert/strict';
import { messageBody, inputText } from '../src/lib/coachSuggestions.ts';

test('messageBody: 문자열은 텍스트 키로', () => {
	assert.deepEqual(messageBody('안녕', 'content'), { content: '안녕' });
	assert.deepEqual(messageBody('안녕', 'initial_message'), { initial_message: '안녕' });
});

test('messageBody: 칩은 chip_id 만 보낸다', () => {
	const chip = { chip_id: 'today_advice', text: '오늘 훈련 어떻게 할까요?' };
	assert.deepEqual(messageBody(chip, 'content'), { chip_id: 'today_advice' });
	assert.deepEqual(messageBody(chip, 'initial_message'), { chip_id: 'today_advice' });
});

test('inputText: 칩은 표시 문구', () => {
	assert.equal(inputText('질문'), '질문');
	assert.equal(inputText({ chip_id: 'injury_check', text: '부상 위험은 없나요?' }), '부상 위험은 없나요?');
});
