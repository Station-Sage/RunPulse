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

// A11Y 공통 5단계 — 페이지 문서 계약: 모든 라우트 페이지·오류 화면은 PageHead(또는 <title>)를 가진다.
const pages = files.filter((f) => /\+(page|error)\.svelte$/.test(f) && f.includes('routes'));
// 리다이렉트 전용 페이지(마크업 없음)는 제외.
const REDIRECT_ONLY = new Set(['src/routes/+page.svelte', 'src/routes/library/wellness/+page.svelte']);
const content = (f) => readFileSync(f, 'utf8');
const hasHead = (s) => /<PageHead\b/.test(s) || /<title>/.test(s);
const ownsH1 = (s) => /<h1\b/.test(s) || /<PageHead\b(?![^>]*heading=\{null\})/.test(s);

test('모든 +page/+error 에 PageHead 또는 <title>', () => {
	const bad = pages.filter((f) => !REDIRECT_ONLY.has(f) && !hasHead(content(f)));
	assert.deepEqual(bad, []);
});

// h1 을 라우트 파일이 직접 그리지 않는 페이지(자식 컴포넌트가 그림) — 줄어들 수만 있다(ratchet).
const H1_IN_CHILD = [
	'src/routes/demo/+page.svelte',
	'src/routes/library/[id]/+page.svelte',
	'src/routes/library/[id]/laps/+page.svelte',
	'src/routes/library/[id]/metrics/+page.svelte',
	'src/routes/library/[id]/providers/+page.svelte',
	'src/routes/library/[id]/streams/+page.svelte',
	'src/routes/library/wellness/[date]/+page.svelte',
	'src/routes/coach/plan/[id]/session/[date]/+page.svelte',
	'src/routes/today/+page.svelte',
	'src/routes/welcome/+page.svelte'
];
test('h1 ratchet — 라우트 파일에 h1 이 없는 페이지는 허용 목록에만', () => {
	const noH1 = pages.filter((f) => !REDIRECT_ONLY.has(f) && !ownsH1(content(f))).sort();
	const extra = noH1.filter((f) => !H1_IN_CHILD.includes(f));
	assert.deepEqual(extra, [], '새로 h1 없는 페이지 — PageHead 를 쓰거나 자식 컴포넌트 h1 을 허용 목록에 근거와 함께 추가');
	const improved = H1_IN_CHILD.filter((f) => !noH1.includes(f));
	assert.deepEqual(improved, [], '개선됨 — 허용 목록에서 제거');
});

test('PageHead 는 title 필수·sr-only/h1 null 처리', () => {
	const s = content('src/lib/components/ui/PageHead.svelte');
	assert.match(s, /title: string/);
	assert.match(s, /heading === undefined/);
});

test('공용 부품: IconButton/TextField/ToggleGroup 은 label 필수', () => {
	const dir = 'src/lib/components/ui/';
	for (const n of ['IconButton', 'TextField', 'ToggleGroup']) {
		const src = readFileSync(dir + n + '.svelte', 'utf8');
		assert.match(src, /\n\t\tlabel[,:]/, `${n}: label prop 필수`);
		assert.doesNotMatch(src, /label\?:/, `${n}: label 은 선택이 될 수 없다`);
	}
	const chip = readFileSync(dir + 'ToggleChip.svelte', 'utf8');
	assert.match(chip, /aria-pressed=\{mode === 'multi'/);
	assert.match(chip, /aria-checked=\{mode === 'single'/);
});
