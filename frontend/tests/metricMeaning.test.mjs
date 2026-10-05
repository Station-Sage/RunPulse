import { test } from 'node:test';
import assert from 'node:assert/strict';
import { displayLabel, isComponentMetric, isFlat } from '../src/lib/metricMeaning.ts';
// meaningFor 등급 판정은 서버 src/metrics/bands.py로 이동 — tests/test_metric_bands.py

test('displayLabel: abbr 있으면 괄호로 병기', () => {
	assert.equal(displayLabel({ name_ko: '폼', abbr: 'TSB' }), '폼 (TSB)');
});

test('displayLabel: abbr 없으면 name_ko만', () => {
	assert.equal(displayLabel({ name_ko: '수면 점수', abbr: null }), '수면 점수');
});

test('isComponentMetric: parent 있으면 true', () => {
	assert.equal(isComponentMetric('X (parent: utrs)'), true);
});

test('isComponentMetric: 일반 라벨은 false', () => {
	assert.equal(isComponentMetric('폼'), false);
});

test('isFlat: 모두 같은 값', () => {
	assert.equal(isFlat([100, 100, 100]), true);
});

test('isFlat: null 포함 다른 값', () => {
	assert.equal(isFlat([100, null, 99]), false);
});

test('isFlat: 단일 값은 false', () => {
	assert.equal(isFlat([100]), false);
});

import { sparkCaption } from '../src/lib/metricMeaning.ts';
test('sparkCaption: 방향·변화율·변동 없음', () => {
	assert.equal(sparkCaption(null), null);
	assert.equal(sparkCaption({ abs: -3, pct: -6.2, days: 14 }), '14일 · ▼6.2%');
	assert.equal(sparkCaption({ abs: 12, pct: 24, days: 7 }), '7일 · ▲24%');
	assert.equal(sparkCaption({ abs: 0.01, pct: 0.1, days: 14 }), '14일 · 변동 없음');
	assert.equal(sparkCaption({ abs: 2.5, pct: null, days: 14 }), '14일 · ▲2.5');
});

test('cardSubline: 힌트 우선, 설명 폴백, 둘 다 없으면 null', async () => {
	const { cardSubline } = await import('../src/lib/metricMeaning.ts');
	assert.equal(cardSubline({ description_short: 'd', action_hint: 'h' }), 'h');
	assert.equal(cardSubline({ description_short: 'd', action_hint: null }), 'd');
	assert.equal(cardSubline({}), null);
});
