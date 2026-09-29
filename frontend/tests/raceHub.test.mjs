import { test } from 'node:test';
import assert from 'node:assert/strict';
import { gapVerdict, countdownLabel, distanceLabel, signedTsb, raceSummaryParts, trendDelta } from '../src/lib/raceHub.ts';
// formBand 등급 판정은 서버 src/metrics/bands.py로 이동 — tests/test_metric_bands.py

test('gapVerdict: null은 unknown, 60초 미만은 on', () => {
	assert.equal(gapVerdict(null).tone, 'unknown');
	assert.equal(gapVerdict(30).tone, 'on');
	assert.equal(gapVerdict(-59).tone, 'on');
});

test('gapVerdict: 느림/빠름 문구', () => {
	const slow = gapVerdict(252);
	assert.equal(slow.tone, 'behind');
	assert.equal(slow.label, '목표보다 4분 12초 느림');
	const fast = gapVerdict(-3700);
	assert.equal(fast.tone, 'ahead');
	assert.equal(fast.label, '목표보다 1시간 1분 빠름');
});

test('countdownLabel: D-day 경계', () => {
	assert.equal(countdownLabel(31), 'D-31');
	assert.equal(countdownLabel(0), 'D-DAY');
	assert.equal(countdownLabel(-3), 'D+3');
});

test('distanceLabel: 표준 거리 근사와 그 외', () => {
	assert.equal(distanceLabel(42.195), '풀 마라톤');
	assert.equal(distanceLabel(21.1), '하프');
	assert.equal(distanceLabel(10), '10K');
	assert.equal(distanceLabel(5), '5K');
	assert.equal(distanceLabel(15), '15.0km');
});

test('signedTsb: 부호 표기', () => {
	assert.equal(signedTsb(12.7), '+13');
	assert.equal(signedTsb(-0.6), '−1');
	assert.equal(signedTsb(0.2), '0');
});

test('raceSummaryParts: 예측·범위·목표', () => {
	const base = { days_left: 56, pred_sec: 13200, low_sec: 12360, high_sec: 14580, range_kind: 'model_envelope', target_sec: 11940 };
	assert.deepEqual(raceSummaryParts(base), ['D-56', '예측 3:40 (모델 범위 3:26–4:03)', '목표 3:19']);
	assert.deepEqual(raceSummaryParts({ ...base, range_kind: 'calibrated80' }).at(1), '예측 3:40 (3:26–4:03)');
});

test('raceSummaryParts: 예측·목표 없음', () => {
	const r = raceSummaryParts({ days_left: 0, pred_sec: null, low_sec: null, high_sec: null, range_kind: null, target_sec: null });
	assert.deepEqual(r, ['D-DAY', '예측 수집 중']);
});

test('trendDelta: 빨라짐·느려짐·변화 없음·점 부족', () => {
	const h = (a, b) => [{ date: 'a', value: a }, { date: 'b', value: b }];
	assert.equal(trendDelta(h(13500, 13200)).label, '90일간 5분 0초 빨라짐');
	assert.equal(trendDelta(h(13200, 13290)).label, '90일간 1분 30초 느려짐');
	assert.equal(trendDelta(h(13200, 13210)).label, '90일간 거의 변화 없음');
	assert.equal(trendDelta([{ date: 'a', value: 1 }]), null);
});
