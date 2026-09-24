import { test } from 'node:test';
import assert from 'node:assert/strict';
import { gapTone, formatGap, predictionToSeries } from '../src/lib/raceHub.ts';

test('gapTone: 음수=green, null·0=teal, 양수=amber', () => {
	assert.equal(gapTone(-60), 'green');
	assert.equal(gapTone(null), 'teal');
	assert.equal(gapTone(0), 'teal');
	assert.equal(gapTone(120), 'amber');
	assert.equal(gapTone(1), 'amber');
	assert.equal(gapTone(-1), 'green');
});

test('formatGap: 분:초 형식 반환', () => {
	assert.equal(formatGap(143), '+2:23');
	assert.equal(formatGap(-105), '-1:45');
	assert.equal(formatGap(60), '+1:00');
	assert.equal(formatGap(0), '±0:00');
	assert.equal(formatGap(-3600), '-60:00');
	assert.equal(formatGap(3661), '+61:01');
});

test('predictionToSeries: 이력 배열을 TrendSeries로 변환', () => {
	const history = [
		{ date: '2026-09-01', value: 10000 },
		{ date: '2026-09-15', value: 9800 }
	];
	const series = predictionToSeries(history, '#22c55e');
	assert.equal(series.key, 'pred');
	assert.equal(series.label, '예측');
	assert.equal(series.color, '#22c55e');
	assert.equal(series.points.length, 2);
	assert.equal(series.points[0].date, '2026-09-01');
	assert.equal(series.points[0].value, 10000);
	assert.equal(series.points[1].date, '2026-09-15');
	assert.equal(series.points[1].value, 9800);
});

test('predictionToSeries: 빈 이력은 빈 points', () => {
	const series = predictionToSeries([], '#14b8a6');
	assert.equal(series.points.length, 0);
});
