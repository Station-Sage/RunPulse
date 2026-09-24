import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
	routePoints,
	downsample,
	projectRoute,
	robustRange,
	lerpColor,
	segmentColor
} from '../src/lib/routeGeometry.ts';

test('routePoints: 유효한 GPS 점만, pace는 speed_ms에서 환산', () => {
	const pts = routePoints([
		{ latitude: 37.5, longitude: 127, speed_ms: 2.5, heart_rate: 140 },
		{ latitude: null, longitude: 127 },
		{ latitude: NaN, longitude: 127 },
		{ latitude: 0, longitude: 0 },
		{ latitude: 91, longitude: 10 },
		{ latitude: 37.6, longitude: 127.1, speed_ms: 0 }
	]);
	assert.equal(pts.length, 2);
	assert.equal(pts[0].pace, 400);
	assert.equal(pts[0].hr, 140);
	assert.equal(pts[1].pace, null);
});

test('downsample: 첫·끝 포함, 짧으면 그대로', () => {
	const a = Array.from({ length: 10 }, (_, i) => i);
	const d = downsample(a, 4);
	assert.equal(d.length, 4);
	assert.equal(d[0], 0);
	assert.equal(d[3], 9);
	assert.deepEqual(downsample([1, 2, 3], 10), [1, 2, 3]);
});

test('projectRoute: 적도 근처 정사각 범위는 정사각형', () => {
	const r = projectRoute(
		[
			{ lat: 0, lng: 0.001, pace: null, hr: null },
			{ lat: 0.01, lng: 0.011, pace: null, hr: null }
		],
		320,
		12
	);
	assert.ok(Math.abs(r.width - r.height) < 0.5);
});

test('projectRoute: 위도만 변하면 폭은 2*pad, 북쪽이 위(y 작음)', () => {
	const r = projectRoute(
		[
			{ lat: 37.5, lng: 127, pace: null, hr: null },
			{ lat: 37.51, lng: 127, pace: null, hr: null },
			{ lat: 37.52, lng: 127, pace: null, hr: null }
		],
		320,
		12
	);
	assert.equal(r.width, 24);
	assert.ok(r.points[2].y < r.points[0].y);
});

test('projectRoute: 점 1개·동일 좌표는 null', () => {
	assert.equal(projectRoute([{ lat: 1, lng: 1, pace: null, hr: null }], 320, 12), null);
	assert.equal(
		projectRoute(
			[
				{ lat: 1, lng: 1, pace: null, hr: null },
				{ lat: 1, lng: 1, pace: null, hr: null }
			],
			320,
			12
		),
		null
	);
});

test('robustRange: 5~95퍼센타일, null 무시, 부족하면 null', () => {
	const v = Array.from({ length: 100 }, (_, i) => i + 1);
	const r = robustRange([...v, null]);
	assert.ok(r.lo >= 5 && r.lo <= 7);
	assert.ok(r.hi >= 94 && r.hi <= 96);
	assert.equal(robustRange([5]), null);
	const same = robustRange([3, 3, 3]);
	assert.equal(same.hi, same.lo + 1);
});

test('lerpColor: 중간값·clamp', () => {
	assert.equal(lerpColor('#000000', '#ffffff', 0.5), '#808080');
	assert.equal(lerpColor('#000000', '#ffffff', -1), '#000000');
	assert.equal(lerpColor('#000000', '#ffffff', 5), '#ffffff');
});

test('segmentColor: 값 없음은 회색, 범위 양끝은 모드 색', () => {
	const range = { lo: 300, hi: 500 };
	assert.equal(segmentColor(null, range, 'pace'), '#64748b');
	assert.equal(segmentColor(300, range, 'pace'), '#3b82f6');
	assert.equal(segmentColor(500, range, 'pace'), '#f97316');
});
