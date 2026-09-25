import { test } from 'node:test';
import assert from 'node:assert/strict';
import { asOfLabel, localDateString } from '../src/lib/asOf.ts';

test('asOfLabel: 오늘이면 "오늘 지금까지 반영"', () => {
	assert.equal(asOfLabel('2026-09-25', '2026-09-25'), '9월 25일 · 오늘 지금까지 반영');
});

test('asOfLabel: 어제면 "기준"', () => {
	assert.equal(asOfLabel('2026-09-24', '2026-09-25'), '9월 24일 기준');
});

test('localDateString: Date 객체에서 YYYY-MM-DD', () => {
	assert.equal(localDateString(new Date(2026, 8, 5)), '2026-09-05');
});
