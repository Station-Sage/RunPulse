import { test } from 'node:test';
import assert from 'node:assert/strict';
import { displayLabel, isComponentMetric, isFlat } from '../src/lib/metricMeaning.ts';
// meaningFor 등급 판정은 서버 src/metrics/bands.py로 이동 — tests/test_metric_bands.py

test('displayLabel: 알려진 메트릭 한국어 라벨', () => {
	assert.equal(displayLabel('tsb', 'Training Stress Balance'), '폼 (TSB)');
});

test('displayLabel: (parent: xxx) 제거', () => {
	assert.equal(
		displayLabel('utrs_tsb', 'UTRS 구성요소 - TSB 정규화값 (parent: utrs)'),
		'UTRS 구성요소 - TSB 정규화값'
	);
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
