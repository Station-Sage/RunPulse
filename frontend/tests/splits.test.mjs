import { test } from 'node:test';
import assert from 'node:assert/strict';
import { computeSplits, cumulativeDistance, sampleTimes } from '../src/lib/splits.ts';

// 1초 간격 스트림: n샘플, 속도(m/s) 함수, 옵션
function make(n, speedAt, opts = {}) {
	return Array.from({ length: n }, (_, i) => ({
		elapsed_sec: opts.index ? i : i,
		distance_m: opts.dist ? opts.dist(i) : null,
		speed_ms: speedAt(i),
		heart_rate: opts.hr === undefined ? null : opts.hr,
		altitude_m: opts.alt ? opts.alt(i) : null
	}));
}

test('등속 4 m/s, 1000초·4000m → 250초짜리 4구간', () => {
	const s = computeSplits(make(1001, () => 4), 1000, 4000);
	assert.equal(s.length, 4);
	s.forEach((x, i) => {
		assert.equal(x.km, i + 1);
		assert.ok(Math.abs(x.sec - 250) <= 1);
		assert.ok(Math.abs(x.paceSecKm - 250) <= 1);
	});
});

test('distance_m가 있으면 그 값을 사용', () => {
	const s = computeSplits(make(1001, () => null, { dist: (i) => i * 4 }), 1000, 4000);
	assert.equal(s.length, 4);
	assert.ok(Math.abs(s[0].sec - 250) <= 1);
});

test('elapsed_sec가 인덱스(501샘플)여도 총 시간에 맞춰 재환산', () => {
	const stream = make(501, () => 4, { index: true });
	const t = sampleTimes(stream, 1000);
	assert.equal(t[500], 1000);
	const s = computeSplits(stream, 1000, 4000);
	assert.equal(s.length, 4);
	assert.ok(Math.abs(s[0].sec - 250) <= 1);
});

test('총 거리 2500m → 3구간, 마지막은 500m 부분 구간', () => {
	const s = computeSplits(make(1001, () => 4), 1000, 2500);
	assert.equal(s.length, 3);
	assert.ok(Math.abs(s[2].distanceM - 500) < 1);
	assert.ok(Math.abs(s[2].paceSecKm - s[2].sec / 0.5) < 0.5);
});

test('재구성 불가 입력은 []', () => {
	assert.deepEqual(computeSplits(make(1001, () => 4), 1000, 800), []);
	assert.deepEqual(computeSplits(make(1, () => 4), 1000, 4000), []);
	assert.deepEqual(computeSplits(make(1001, () => 4), 0, 4000), []);
});

test('심박 평균: 일정하면 그 값, 전부 null이면 null', () => {
	const a = computeSplits(make(1001, () => 4, { hr: 150 }), 1000, 4000);
	assert.ok(a.every((x) => x.avgHr === 150));
	const b = computeSplits(make(1001, () => 4), 1000, 4000);
	assert.ok(b.every((x) => x.avgHr === null));
});

test('고도 0→80 선형이면 구간마다 +20', () => {
	const s = computeSplits(make(1001, () => 4, { alt: (i) => i * 0.08 }), 1000, 4000);
	assert.ok(s.every((x) => Math.abs(x.elevDelta - 20) < 0.2));
});

test('점점 빨라지면(2→4 m/s) 페이스가 단조 감소', () => {
	const s = computeSplits(make(1501, (i) => 2 + (2 * i) / 1500), 1500, 4500);
	for (let i = 1; i < s.length; i++) assert.ok(s[i].paceSecKm < s[i - 1].paceSecKm);
});

test('cumulativeDistance: 속도 적분 후 총 거리로 스케일', () => {
	const d = cumulativeDistance(make(101, () => 3), 100, 600);
	assert.ok(Math.abs(d[100] - 600) < 1e-6);
});
