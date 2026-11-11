// S4-89 — ContextChips 첫 조회는 onChange 를 부르지 않는다(오늘 화면 이중 로드 방지) 정적 가드.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const src = readFileSync(new URL('../src/lib/components/ContextChips.svelte', import.meta.url), 'utf8');

test('마운트 시 effect 는 fetchList 만 부른다(onChange 경로인 reload 아님)', () => {
	const eff = src.match(/\$effect\(\(\) => \{([^}]*)\}\);/);
	assert.ok(eff, '$effect 블록이 있어야 한다');
	assert.match(eff[1], /fetchList\(\)/);
	assert.doesNotMatch(eff[1], /reload\(\)/);
});

test('fetchList 본문에는 onChange 호출이 없다', () => {
	const body = src.match(/async function fetchList\(\) \{([\s\S]*?)\n\t\}/);
	assert.ok(body);
	assert.doesNotMatch(body[1], /onChange/);
});

test('사용자 변경 경로(reload)는 onChange 를 유지한다', () => {
	const body = src.match(/async function reload\(\) \{([\s\S]*?)\n\t\}/);
	assert.ok(body);
	assert.match(body[1], /onChange\?\.\(\)/);
});
