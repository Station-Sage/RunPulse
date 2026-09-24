// frontend/tests/trendChart.test.mjs
// trendChart.ts 순수 함수 단위 테스트 — 실행: npm run test:unit (Node 내장 test runner)
import test from 'node:test';
import assert from 'node:assert/strict';
import { changeLabel, sharedYRange } from '../src/lib/trendChart.ts';

// ── changeLabel ──────────────────────────────────────────────────────────────

test('changeLabel: null 입력 → "—"', () => {
	assert.equal(changeLabel(null, 10), '—');
	assert.equal(changeLabel(10, null), '—');
	assert.equal(changeLabel(null, null), '—');
});

test('changeLabel: prev < 10 → 절대 변화', () => {
	// CTL 4.5 → 37.9 케이스: prev=4.5 < 10 이므로 퍼센트 대신 절대값
	const result = changeLabel(37.9, 4.5);
	assert.equal(result, '+33.4');
});

test('changeLabel: prev >= 10 → 퍼센트', () => {
	// CTL 30 → 37.5 케이스: prev=30 >= 10 이므로 퍼센트
	const result = changeLabel(37.5, 30);
	assert.equal(result, '+25.0%');
});

test('changeLabel: 음수 변화, prev >= 10', () => {
	const result = changeLabel(20, 40);
	assert.equal(result, '-50.0%');
});

test('changeLabel: 음수 변화, prev < 10', () => {
	const result = changeLabel(3, 8);
	assert.equal(result, '-5.0');
});

test('changeLabel: TSB 음수 prev (|prev| < 10) → 절대 변화', () => {
	// TSB -5 → -2 케이스: |prev|=5 < 10 → 절대 변화
	const result = changeLabel(-2, -5);
	assert.equal(result, '+3.0');
});

test('changeLabel: prev === 0 → 절대 변화 (0으로 나누기 방지)', () => {
	const result = changeLabel(5, 0);
	assert.equal(result, '+5.0');
});

test('changeLabel: 변화 없음, prev >= 10', () => {
	const result = changeLabel(50, 50);
	assert.equal(result, '+0.0%');
});

test('changeLabel: 변화 없음, prev < 10', () => {
	const result = changeLabel(5, 5);
	assert.equal(result, '+0.0');
});

// ── sharedYRange ─────────────────────────────────────────────────────────────

test('sharedYRange: 빈 계열 배열 → { min:0, max:1 }', () => {
	const r = sharedYRange([]);
	assert.deepEqual(r, { min: 0, max: 1 });
});

test('sharedYRange: 전부 null → { min:0, max:1 }', () => {
	const r = sharedYRange([{ values: [null, null], color: '#000' }]);
	assert.deepEqual(r, { min: 0, max: 1 });
});

test('sharedYRange: 단일 계열', () => {
	const r = sharedYRange([{ values: [10, 20, 30], color: '#000' }]);
	assert.deepEqual(r, { min: 10, max: 30 });
});

test('sharedYRange: 다계열 — 공통 범위', () => {
	const r = sharedYRange([
		{ values: [10, 20, 30], color: '#000' }, // CTL
		{ values: [15, 35, 25], color: '#f00' }  // ATL
	]);
	assert.deepEqual(r, { min: 10, max: 35 });
});

test('sharedYRange: null 포함 계열 — null 무시', () => {
	const r = sharedYRange([{ values: [null, 5, null, 20], color: '#000' }]);
	assert.deepEqual(r, { min: 5, max: 20 });
});

test('sharedYRange: min === max → ±1 패딩', () => {
	const r = sharedYRange([{ values: [42, 42], color: '#000' }]);
	assert.deepEqual(r, { min: 41, max: 43 });
});

test('sharedYRange: CTL/ATL 공통 범위 검증 (실데이터 유사 케이스)', () => {
	// CTL 4.5~37.9, ATL 5~45: 공통 범위는 4.5~45
	const r = sharedYRange([
		{ values: [4.5, 20, 37.9], color: '#3b82f6' },
		{ values: [5, 25, 45], color: '#f59e0b' }
	]);
	assert.equal(r.min, 4.5);
	assert.equal(r.max, 45);
});
