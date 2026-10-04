// formatUnitValue 순수 함수 테스트 — 실행: npm run test:unit (Node 내장 test runner)
import test from 'node:test';
import assert from 'node:assert/strict';
import { formatUnitValue } from '../src/lib/format.ts';

test('sec → 시:분:초, unit 빈 문자열', () => {
	const r = formatUnitValue(22440, 'sec');
	assert.equal(r.display, '6:14:00');
	assert.equal(r.unit, '');
});

test('sec → h:mm:ss (8357 sec = 2h 19m 17s)', () => {
	const r = formatUnitValue(8357, 'sec');
	assert.equal(r.display, '2:19:17');
	assert.equal(r.unit, '');
});

test('sec/km → m:ss/km 페이스, unit 빈 문자열', () => {
	const r = formatUnitValue(300, 'sec/km');
	assert.equal(r.display, '5:00/km');
	assert.equal(r.unit, '');
});

test('m ≥ 1000 → km 소수 1자리, unit km', () => {
	const r = formatUnitValue(24207.9, 'm');
	assert.equal(r.display, '24.2');
	assert.equal(r.unit, 'km');
});

test('m < 1000 → 소수 1자리, unit m 그대로', () => {
	const r = formatUnitValue(26.0799999, 'm');
	assert.equal(r.display, '26.1');
	assert.equal(r.unit, 'm');
});

test('값 ≥ 100 → 정수, unit 그대로', () => {
	const r = formatUnitValue(165.3, 'bpm');
	assert.equal(r.display, '165');
	assert.equal(r.unit, 'bpm');
});

test('값 < 100 → 소수 1자리, unit 그대로', () => {
	const r = formatUnitValue(75.5, 'bpm');
	assert.equal(r.display, '75.5');
	assert.equal(r.unit, 'bpm');
});

test('unit 빈 문자열 → 일반 반올림 규칙, unit 빈 문자열 그대로', () => {
	const r = formatUnitValue(3.14, '');
	assert.equal(r.display, '3.1');
	assert.equal(r.unit, '');
});

test('정수는 소수점 없이(48 ms → "48", 58 → "58")', () => {
	assert.equal(formatUnitValue(48, 'ms').display, '48');
	assert.equal(formatUnitValue(58, '').display, '58');
});

test('소수 끝 0은 제거(3.04 → "3")', () => {
	assert.equal(formatUnitValue(3.04, '').display, '3');
});

test('displayUnit: 시간·페이스 단위는 숨김', async () => {
	const { displayUnit } = await import('../src/lib/format.ts');
	assert.equal(displayUnit('sec'), '');
	assert.equal(displayUnit('sec/km'), '');
	assert.equal(displayUnit(null), '');
	assert.equal(displayUnit('bpm'), 'bpm');
});
