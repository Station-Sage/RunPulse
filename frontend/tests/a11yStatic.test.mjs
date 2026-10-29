// OVL-8 정적 가드 — 모든 role="dialog" 는 use:modal, role="alertdialog" 는 금지(role="group"+inlineConfirm).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

function walk(dir, out = []) {
	for (const n of readdirSync(dir)) {
		const p = join(dir, n);
		if (statSync(p).isDirectory()) walk(p, out);
		else if (p.endsWith('.svelte')) out.push(p);
	}
	return out;
}
const files = walk('src');

test('role="alertdialog" 없음', () => {
	const bad = files.filter((f) => readFileSync(f, 'utf8').includes('role="alertdialog"'));
	assert.deepEqual(bad, []);
});

test('role="dialog" 요소는 같은 요소에 use:modal', () => {
	const bad = [];
	for (const f of files) {
		const s = readFileSync(f, 'utf8');
		for (const m of s.matchAll(/<(\w+)\b[^<>]*?role="dialog"[^<>]*?>/gs)) {
			if (!m[0].includes('use:modal')) bad.push(f);
		}
	}
	assert.deepEqual(bad, []);
});

// A11Y 공통 2단계 — 색 리터럴 가드: 컴포넌트·라우트·lib 에 hex/rgb()/text-white/bg-black/기본 팔레트 클래스 금지(토큰만).
const LITERAL = /#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b(?![\w-])|\brgba?\(|\b(?:text|bg|border|ring|fill|stroke)-(?:white|black)\b|\bbg-black\/\d+|\b(?:text|bg|border|fill|stroke)-(?:red|amber|teal|sky|rose|slate|gray|blue|green|emerald|violet|orange|yellow)-\d{2,3}\b/g;
function srcFiles(dir, out = []) {
	for (const n of readdirSync(dir)) {
		const p = join(dir, n);
		if (statSync(p).isDirectory()) srcFiles(p, out);
		else if (/\.(svelte|ts)$/.test(p)) out.push(p);
	}
	return out;
}
export function colorLiterals(text) {
	const hits = [];
	for (const line of text.split('\n')) {
		if (/^\s*(\/\/|\*|\/\*)/.test(line)) continue;
		hits.push(...(line.replace(/\/\*.*?\*\//g, '').match(LITERAL) ?? []));
	}
	return hits;
}

test('색 리터럴 없음 — 토큰(var(--color-*))·시맨틱 클래스만', () => {
	const bad = [];
	for (const f of srcFiles('src')) {
		if (f.endsWith('lib/theme/theme.ts')) continue; // theme-color meta 값(브라우저 UI 색)은 토큰이 아니라 리터럴
		const h = colorLiterals(readFileSync(f, 'utf8'));
		if (h.length) bad.push(`${f}: ${h.join(' ')}`);
	}
	assert.deepEqual(bad, []);
});

test('colorLiterals: 대표 위반을 잡고 토큰은 통과', () => {
	assert.equal(colorLiterals('<p class="text-white bg-black/40">').length, 2);
	assert.equal(colorLiterals('stroke="#fff" fill="rgb(0 0 0)"').length, 2);
	assert.equal(colorLiterals('<p class="text-red-500">').length, 1);
	assert.equal(colorLiterals('<p class="bg-scrim text-fg-on-accent" style="stroke: var(--color-chart-ctl)">').length, 0);
	assert.equal(colorLiterals('// #ef4444 주석').length, 0);
});
