// E-29 — 폰트는 Vite 자산(해시 파일명·immutable)으로 번들, base 하드코딩 금지. 실행: npm run test:unit
import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

test('layout.css 의 @font-face 는 상대 경로이고 대상 파일이 있다', () => {
	const css = readFileSync(new URL('../src/routes/layout.css', import.meta.url), 'utf8');
	assert.equal(/url\(['"]?\/v2\//.test(css), false);
	const urls = [...css.matchAll(/url\('(\.\.\/lib\/assets\/fonts\/[^']+)'\)/g)].map((m) => m[1]);
	assert.ok(urls.length >= 2);
	for (const u of urls) assert.ok(existsSync(new URL(`../src/routes/${u}`, import.meta.url)), u);
});
