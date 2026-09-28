// §C4 값 포맷 규칙(ux-review-2026-09/10-today/design.md) 신규 함수 테스트.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
	formatDistance,
	formatLoad,
	formatForm,
	formatFormDetail,
	formatRatio,
	formatPercent,
	formatPercentile,
	formatScore,
	formatHeartRate,
	formatChange,
	formatTimeDiff,
	formatPrediction,
	formatDateLong,
	formatDateShort,
	MINUS
} from '../src/lib/format.ts';

test('formatDistance — 1km 미만은 m, 이상은 km(D1c 소수 자리수 옵션)', () => {
	assert.equal(formatDistance(525), '525m');
	assert.equal(formatDistance(9300), '9.3km');
	assert.equal(formatDistance(9300, 2), '9.30km');
});

test('formatLoad — 부하는 소수 1자리, 부호 없음', () => {
	assert.equal(formatLoad(72.64), '72.6');
});

test('formatForm — TSB 요약은 부호 있는 정수, U+2212 사용', () => {
	assert.equal(formatForm(15.4), '+15');
	assert.equal(formatForm(-9.2), `${MINUS}9`);
	assert.equal(formatForm(0), '0');
});

test('formatFormDetail — TSB 분해 공식은 소수 1자리', () => {
	assert.equal(formatFormDetail(-14.03), `${MINUS}14.0`);
});

test('formatRatio — ACWR 등은 소수 2자리', () => {
	assert.equal(formatRatio(1.123), '1.12');
});

test('formatPercent·formatPercentile', () => {
	assert.equal(formatPercent(48.6), '49%');
	assert.equal(formatPercentile(77.6), 'p78');
});

test('formatScore·formatHeartRate', () => {
	assert.equal(formatScore(59.6), '60');
	assert.equal(formatHeartRate(137.4), '137 bpm');
});

test('formatChange — 항상 부호, 0은 부호 없이 0', () => {
	assert.equal(formatChange(1), '+1');
	assert.equal(formatChange(-1), `${MINUS}1`);
	assert.equal(formatChange(0), '0');
	assert.equal(formatChange(4.2, 1), '+4.2');
});

test('formatTimeDiff — n분(±)', () => {
	assert.equal(formatTimeDiff(21 * 60), '+21분');
	assert.equal(formatTimeDiff(-7 * 60), `${MINUS}7분`);
	assert.equal(formatTimeDiff(20), '0분');
});

test('formatPrediction — 신뢰도 <0.5는 범위 병기, >=0.5는 h:mm:ss', () => {
	assert.equal(formatPrediction(13223, 0.4, [12360, 14580]), '3:40 (3:26–4:03)');
	assert.equal(formatPrediction(13223, 0.7, [12360, 14580]), '3:40:23');
	assert.equal(formatPrediction(3318, 0.9, null), '55:18');
});

test('formatDateLong·formatDateShort — 한국어 요일 병기', () => {
	assert.equal(formatDateLong('2026-09-27'), '9월 27일 (일)');
	assert.equal(formatDateShort('2026-09-27'), '9/27(일)');
});
