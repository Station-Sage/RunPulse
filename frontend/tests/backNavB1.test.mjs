// V2-REPAIR B1 — 뒤로가기 규칙·Button 스타일 순수 함수.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { backTarget, parentPath, safeInternalPath, withFrom } from '../src/lib/backNav.ts';
import { buttonClass } from '../src/lib/buttonStyle.ts';

test('safeInternalPath: 내부 경로만 통과, 외부·// 는 거부', () => {
	assert.equal(safeInternalPath('/library/activities?month=2026-09'), '/library/activities?month=2026-09');
	assert.equal(safeInternalPath('//evil.com'), null);
	assert.equal(safeInternalPath('/\\evil.com'), null);
	assert.equal(safeInternalPath('https://evil.com'), null);
	assert.equal(safeInternalPath('javascript:alert(1)'), null);
	assert.equal(safeInternalPath('/a\nb'), null);
	assert.equal(safeInternalPath(''), null);
	assert.equal(safeInternalPath(null), null);
	assert.equal(safeInternalPath('/x/coach', '/x'), '/coach');
});

test('parentPath: 마지막 세그먼트를 뗀다, 루트는 null', () => {
	assert.equal(parentPath('/library/123/laps'), '/library/123');
	assert.equal(parentPath('/coach/plan/'), '/coach');
	assert.equal(parentPath('/coach'), null);
	assert.equal(parentPath('/'), null);
});

test('backTarget: from 우선, 아니면 부모, 마지막은 fallback', () => {
	assert.equal(backTarget('/library/9', '/today'), '/today');
	assert.equal(backTarget('/library/9', 'https://evil.com'), '/library');
	assert.equal(backTarget('/library/9', null), '/library');
	assert.equal(backTarget('/coach', null), '/today');
	assert.equal(backTarget('/coach', null, '', '/library'), '/library');
});

test('withFrom: 돌아올 자리를 달고, 이미 쿼리가 있으면 & 로 잇는다', () => {
	assert.equal(withFrom('/data/sources', '/welcome'), '/data/sources?from=%2Fwelcome');
	assert.equal(withFrom('/x?a=1', '/welcome'), '/x?a=1&from=%2Fwelcome');
	assert.equal(withFrom('/x', '//evil'), '/x');
});

test('buttonClass: variant 별 클래스, 44px 보장, full', () => {
	assert.match(buttonClass('primary'), /bg-fg-primary/);
	assert.match(buttonClass('danger'), /text-semantic-red/);
	assert.match(buttonClass('ghost', true), /w-full/);
	for (const v of ['primary', 'secondary', 'ghost', 'danger']) assert.match(buttonClass(v), /min-h-11/);
});
