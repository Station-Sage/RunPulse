import { test } from 'node:test';
import assert from 'node:assert/strict';
import { meaningFor, displayLabel, isComponentMetric, isFlat } from '../src/lib/metricMeaning.ts';

test('meaningFor: tsb 레이스 최적', () => {
	const r = meaningFor('tsb', 8.8);
	assert.deepEqual(r, { status: 'excellent', note: '레이스 최적' });
});

test('meaningFor: tsb 과부하', () => {
	assert.equal(meaningFor('tsb', -25).note, '과부하');
});

test('meaningFor: tsb 휴식 과다', () => {
	assert.equal(meaningFor('tsb', 30).note, '휴식 과다');
});

test('meaningFor: utrs 좋음', () => {
	assert.equal(meaningFor('utrs', 64.7).note, '좋음');
});

test('meaningFor: utrs 매우 좋음', () => {
	assert.equal(meaningFor('utrs', 85).status, 'excellent');
});

test('meaningFor: cirs 낮음', () => {
	assert.equal(meaningFor('cirs', 25).status, 'good');
});

test('meaningFor: acwr 저부하', () => {
	assert.equal(meaningFor('acwr', 0.76).note, '저부하');
});

test('meaningFor: acwr 적정', () => {
	assert.equal(meaningFor('acwr', 1.0).note, '적정');
});

test('meaningFor: training_effect_aerobic 매우 높은 자극', () => {
	assert.equal(meaningFor('training_effect_aerobic', 4.5).note, '매우 높은 자극');
});

test('meaningFor: training_effect_aerobic 큰 개선', () => {
	assert.equal(meaningFor('training_effect_aerobic', 3.2).note, '큰 개선');
});

test('meaningFor: aerobic_decoupling 절댓값 적용', () => {
	assert.equal(meaningFor('aerobic_decoupling', -6).note, '양호');
});

test('meaningFor: 알 수 없는 메트릭은 null', () => {
	assert.equal(meaningFor('trimp', 200), null);
});

test('meaningFor: null 값은 null', () => {
	assert.equal(meaningFor('tsb', null), null);
});

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
