// V2-AUDIT 묶음 D(데이터·설정) 프런트 헬퍼.
import test from 'node:test';
import assert from 'node:assert/strict';
import { parseProfileInput } from '../src/lib/profileRows.ts';
import { scheduleTime } from '../src/lib/dataArea.ts';
import { keyFormatError } from '../src/lib/aiSettings.ts';
import { PLAN_ICS_URL, progressText, quickResultText } from '../src/lib/exports.ts';
import { outcomeFromError } from '../src/lib/syncState.ts';

test('D-30 parseProfileInput: m:ss 만 허용', () => {
	assert.equal(parseProfileInput('threshold_pace', '5:30'), 330);
	assert.equal(parseProfileInput('threshold_pace', '5:30:99'), undefined);
	assert.equal(parseProfileInput('threshold_pace', '5:3'), undefined);
	assert.equal(parseProfileInput('threshold_pace', '-5:30'), undefined);
	assert.equal(parseProfileInput('threshold_pace', '5.5:30'), undefined);
});

test('D-31 scheduleTime: 오늘/어제/내일/날짜', () => {
	assert.equal(scheduleTime('2026-11-10T01:38:00+09:00', '2026-11-10'), '오늘 01:38');
	assert.equal(scheduleTime('2026-11-09T23:10:00', '2026-11-10'), '어제 23:10');
	assert.equal(scheduleTime('2026-11-11T05:38:00', '2026-11-10'), '내일 05:38');
	assert.equal(scheduleTime('2026-11-01T05:38:00', '2026-11-10'), '11월 1일 05:38');
	assert.equal(scheduleTime(null, '2026-11-10'), null);
});

test('D-23 keyFormatError', () => {
	assert.equal(keyFormatError(''), null);
	assert.equal(keyFormatError('  AIzaSy-abc_123  '), null);
	assert.ok(keyFormatError('ab cd'));
	assert.ok(keyFormatError('ab\ncd'));
	assert.ok(keyFormatError('<b>x</b>'));
	assert.ok(keyFormatError('k'.repeat(257)));
});

test('D-02·D-16·D-18 내보내기 문구', () => {
	assert.equal(PLAN_ICS_URL, '/training/export.ics');
	assert.match(quickResultText(0), /기록이 없어/);
	assert.equal(quickResultText(5), '');
	assert.equal(quickResultText(null), '');
	assert.equal(progressText({ progress: { done: 3, total: 12 } }), '만드는 중… 3/12');
	assert.equal(progressText({ progress: null }), '만드는 중…');
});

test('D-05 outcomeFromError: 503 은 네트워크 안내', () => {
	assert.match(outcomeFromError(503, { skipped: [{ provider: 'intervals', code: 'unreachable', message_ko: 'm' }] }).notice, /서버에 연결하지 못했어요/);
	assert.equal(outcomeFromError(503, { skipped: [{ provider: 'intervals', code: 'unreachable', message_ko: 'm' }] }).skipped.length, 1);
});
