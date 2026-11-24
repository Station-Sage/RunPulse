import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

// navigating.to 는 idle 일 때 null, url 도 방어적으로 null 가능 — `to?.url.` 직접 접근은 TypeError.
const SHELL_NAV = fileURLToPath(new URL('../src/lib/components/shell/ShellNav.svelte', import.meta.url));

test('ShellNav 는 navigating.to?.url?.pathname 으로 null 안전 접근', () => {
	const src = readFileSync(SHELL_NAV, 'utf8');
	assert.match(src, /navigating\.to\?\.url\?\.pathname/);
	assert.doesNotMatch(src, /to\?\.url\.pathname/);
});
