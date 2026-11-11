// V2-AUDIT-INDIV 묶음 G(보류 항목 추천안) 프런트 헬퍼 — P-14 롱런 요일, C-17 동의창, M-30 핀 안내.
import test from 'node:test';
import assert from 'node:assert/strict';
import { LONG_RUN_AUTO, longRunOptions, parseLongRunWeekday } from '../src/lib/planPrefill.ts';
import { consentDefaults, consentText, fallbackNames, providerName } from '../src/lib/coachEngine.ts';
import { PINS_DEVICE_NOTE } from '../src/lib/pinnedMetrics.ts';

test('P-14 parseLongRunWeekday: 운동 요일 안의 한 자리 숫자만', () => {
	assert.equal(parseLongRunWeekday('6', [1, 3, 6]), 6);
	assert.equal(parseLongRunWeekday('5', [1, 3, 6]), null);
	assert.equal(parseLongRunWeekday('x', [1]), null);
	assert.equal(parseLongRunWeekday('16', [1]), null);
	assert.equal(parseLongRunWeekday(null, [1]), null);
});

test('P-14 longRunOptions: 자동 + 고른 요일', () => {
	assert.deepEqual(longRunOptions([2, 6]), [
		{ value: LONG_RUN_AUTO, label: '자동(주말 우선)' },
		{ value: '2', label: '수' },
		{ value: '6', label: '일' }
	]);
});

test('C-17 consentDefaults: 동의 전엔 메모 제외·재시도 끔, 저장값은 유지', () => {
	assert.deepEqual(consentDefaults(null), { excludeNotes: true, toolsEnabled: true, fallbackEnabled: false });
	assert.deepEqual(consentDefaults({ exclude_notes: false, tools_enabled: false, fallback_enabled: true }),
		{ excludeNotes: false, toolsEnabled: false, fallbackEnabled: true });
});

test('C-17 consentText: 기본·재시도 제공자를 모두 밝힘', () => {
	const e = { selected: { provider: 'gemini', model: null }, fallback_providers: [{ provider: 'groq', label: 'Groq' }] };
	assert.equal(fallbackNames(e), 'Groq');
	assert.match(consentText(e), /Gemini 서버로 전송돼요/);
	assert.match(consentText(e), /Groq 서버로도 전송돼요\(기본은 꺼짐\)/);
	const solo = { selected: { provider: 'gemini', model: null }, fallback_providers: [] };
	assert.doesNotMatch(consentText(solo), /재시도/);
	assert.equal(providerName('claude'), 'Claude');
});

test('M-30 핀은 이 기기에만 저장된다는 안내', () => {
	assert.equal(PINS_DEVICE_NOTE, '이 기기에만 저장');
});
