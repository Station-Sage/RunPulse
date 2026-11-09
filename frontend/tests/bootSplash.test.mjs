// lib/bootSplash.ts — 첫 로드 정적 로딩 화면 제거 (S-05). 실행: npm run test:unit
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { removeBootSplash, BOOT_SPLASH_ID } from '../src/lib/bootSplash.ts';

test('removeBootSplash: 있으면 지우고 true, 없거나 document 가 없으면 false', () => {
	let removed = 0;
	const doc = { getElementById: (id) => (id === BOOT_SPLASH_ID ? { remove: () => removed++ } : null) };
	assert.equal(removeBootSplash(doc), true);
	assert.equal(removed, 1);
	assert.equal(removeBootSplash({ getElementById: () => null }), false);
	assert.equal(removeBootSplash(undefined), false);
});

test('app.html 의 로딩 화면은 aria-busy 이고 인라인 스크립트가 없다(CSP)', () => {
	const html = readFileSync(new URL('../src/app.html', import.meta.url), 'utf8');
	assert.match(html, new RegExp(`id="${BOOT_SPLASH_ID}" aria-busy="true"`));
	assert.equal(/<script>(?!<\/script>)/.test(html), false);
});
