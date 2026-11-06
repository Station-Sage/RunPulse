// lib/chart/radar.ts — 각도·반경·clamp·결측 점선 구간·마커 (balance-radar §8 T5). 실행: npm run test:unit
import test from 'node:test';
import assert from 'node:assert/strict';
import { axisAngle, clampScore, radiusOf, pointFor, ringPoints, radarShape, labelAnchor, markerPath, SCORE_MAX } from '../src/lib/chart/radar.ts';

test('각도 — 0번 축 12시, 시계 방향 균등', () => {
	assert.equal(axisAngle(0, 6), -Math.PI / 2);
	assert.ok(Math.abs(axisAngle(3, 6) - Math.PI / 2) < 1e-9);
	const p = pointFor(0, 6, 150, 100);
	assert.deepEqual(p, { x: 0, y: -100 });
});

test('반경 — 0~150 clamp', () => {
	assert.equal(SCORE_MAX, 150);
	assert.equal(clampScore(200), 150);
	assert.equal(clampScore(-5), 0);
	assert.equal(radiusOf(75, 100), 50);
	assert.equal(radiusOf(300, 100), 100);
});

test('기준 링 — n개 꼭짓점', () => {
	assert.equal(ringPoints(100, 6, 90).split(' ').length, 6);
});

test('6축 모두 유효 — 실선 6, 점선 0, 채움 6점', () => {
	const s = radarShape([100, 100, 100, 100, 100, 100], 100);
	assert.equal(s.solid.length, 6);
	assert.equal(s.dashed.length, 0);
	assert.equal(s.fill.split(' ').length, 6);
});

test('4축 유효(1·4번 결측) — 결측을 건너뛰는 구간은 점선, 중심으로 꺾지 않음', () => {
	const s = radarShape([100, null, 100, 100, null, 100], 100);
	assert.equal(s.vertices.filter((v) => v === null).length, 2);
	assert.equal(s.solid.length, 2); // 2-3, 5-0
	assert.equal(s.dashed.length, 2); // 0-2, 3-5
	for (const [a, b] of s.dashed) assert.ok(!(a.x === 0 && a.y === 0) && !(b.x === 0 && b.y === 0));
	assert.equal(s.fill.split(' ').length, 4);
});

test('유효 2축 — 채움 없음, 이웃이면 실선 1', () => {
	const s = radarShape([100, 100, null, null, null, null], 100);
	assert.equal(s.fill, '');
	assert.equal(s.solid.length, 1);
	const w = radarShape([100, null, null, null, null, 100], 100);
	assert.equal(w.solid.length, 1);
	assert.equal(radarShape([null, null, null, null, null, null], 100).solid.length, 0);
});

test('라벨 정렬 — 위·아래 middle, 오른쪽 start, 왼쪽 end', () => {
	assert.equal(labelAnchor(0, 6, 100, 10).anchor, 'middle');
	assert.equal(labelAnchor(1, 6, 100, 10).anchor, 'start');
	assert.equal(labelAnchor(3, 6, 100, 10).anchor, 'middle');
	assert.equal(labelAnchor(5, 6, 100, 10).anchor, 'end');
});

test('마커 — 과다 ▲(꼭짓점 위), 부족 ▼(꼭짓점 아래), 균형 null', () => {
	assert.match(markerPath({ x: 0, y: 0 }, 'high', 5), /^M0,-5 /);
	assert.match(markerPath({ x: 0, y: 0 }, 'low', 5), /^M0,5 /);
	assert.equal(markerPath({ x: 0, y: 0 }, 'balanced'), null);
});
