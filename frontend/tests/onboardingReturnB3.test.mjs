// B3: 온보딩에서 나간 화면이 /welcome 단계로 돌아올 수 있는지.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { backTarget, withFrom } from '../src/lib/backNav.ts';

const src = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');

test('withFrom → backTarget 왕복: 쿼리 포함 welcome 단계로 복귀', () => {
	const href = withFrom('/data/sources/intervals', '/welcome?step=1');
	const from = new URL(href, 'http://x').searchParams.get('from');
	assert.equal(backTarget('/data/sources/intervals', from, '', '/data/sources'), '/welcome?step=1');
});

test('외부 from 은 무시하고 소스 목록으로', () => {
	assert.equal(backTarget('/data/sources/intervals', '//evil.com', '', '/data/sources'), '/data/sources');
});

test('Step1·Step3 이탈 링크는 withFrom 으로 단계를 싣는다', () => {
	assert.match(src('lib/components/welcome/Step1Connect.svelte'), /withFrom\('\/data\/sources\/intervals', '\/welcome\?step=1'\)/);
	assert.match(src('lib/components/welcome/Step3Goal.svelte'), /withFrom\('\/coach\/plan\/new', '\/welcome\?step=3'\)/);
});

test('Step4 저장 후 완료 안내', () => {
	assert.match(src('lib/components/welcome/Step4Baseline.svelte'), /완료/);
});
