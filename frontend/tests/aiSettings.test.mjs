import { test } from 'node:test';
import assert from 'node:assert/strict';
import { engineSummary, keyStateText, usageText } from '../src/lib/aiSettings.ts';

const base = { provider: 'gemini', mode: 'llm', chain: [{ provider: 'gemini', model: 'm' }], health: { degraded: false }, last_error_label: null };

test('engineSummary: 상태별 문구', () => {
	assert.equal(engineSummary(base), 'Gemini · 폴백 없음');
	assert.equal(engineSummary({ ...base, chain: [...base.chain, { provider: 'groq', model: 'x' }] }), 'Gemini · 실패 시 Groq');
	assert.equal(engineSummary({ ...base, health: { degraded: true }, last_error_label: '사용량 한도(429)' }), '규칙 기반 · Gemini 오류로 대체 (사용량 한도(429))');
	assert.equal(engineSummary({ ...base, mode: 'rule_by_choice' }), '규칙 기반 · AI를 끔');
	assert.equal(engineSummary({ ...base, mode: 'rule_only' }), '규칙 기반 · API 키가 없어요');
});

test('usageText / keyStateText', () => {
	assert.equal(usageText({ messages: 0, by_provider: {}, fallback: 0, rule: 0, tool_calls: 0 }), '최근 7일 답변이 없어요');
	assert.equal(usageText({ messages: 3, by_provider: { gemini: 2 }, fallback: 1, rule: 0, tool_calls: 4 }),
		'최근 7일 답변 3건 · Gemini 2회 · 규칙 대체 1회 · 데이터 조회 4회');
	assert.equal(keyStateText('invalid'), '키가 거부됐어요');
});
