import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { contrastRatio, relativeLuminance, parseThemeTokens } from '../src/lib/a11y/contrast.ts';
import { PAIRS, THRESHOLD, S3_FLOOR_PAIRS } from '../src/lib/a11y/contrastPairs.ts';

const css = readFileSync(new URL('../src/routes/layout.css', import.meta.url), 'utf8');
const tokens = parseThemeTokens(css);

// 단계 3·4 에서 비운다. 형식: `테마|fg|bg`. 목록에 없는 실패, 목록에 있는데 통과한 항목 모두 실패 처리(ratchet).
const EXPECTED_FAIL = new Set([
	'dark|fg-muted|surface-1',
	'dark|fg-muted|surface-2',
	'dark|semantic-red|surface-2',
	'dark|semantic-red|surface-3',
	'dark|series-3|surface-1',
	'dark|series-3|surface-2',
	'dark|series-3|surface-3'
]);

test('상대휘도·대비비 기준값', () => {
	assert.equal(relativeLuminance('#000000'), 0);
	assert.ok(Math.abs(relativeLuminance('#ffffff') - 1) < 1e-9);
	assert.ok(Math.abs(contrastRatio('#000', '#fff') - 21) < 1e-9);
	assert.ok(Math.abs(contrastRatio('#777777', '#ffffff') - 4.48) < 0.01);
	assert.throws(() => relativeLuminance('rgb(0 0 0)'));
});

test('parseThemeTokens: 다크 @theme 와 var() 한 단계 해석', () => {
	const t = parseThemeTokens(
		"@theme { --color-a: #111111; --color-b: var(--color-a); }\n:root[data-theme='light'] { --color-a: #eeeeee; }"
	);
	assert.equal(t.dark['--color-b'], '#111111');
	assert.equal(t.light['--color-a'], '#eeeeee');
	assert.equal(t.light['--color-b'], '#eeeeee');
	assert.equal(t.lightMedia, null);
	assert.equal(parseThemeTokens('@theme { --color-a: #111; }').light, null);
});

function failures(theme) {
	const set = tokens[theme];
	const out = [];
	for (const p of PAIRS) {
		if (p.themes && !p.themes.includes(theme)) continue;
		const fg = set[`--color-${p.fg}`];
		const bg = set[`--color-${p.bg}`];
		if (!fg || !bg) continue; // 토큰이 아직 없으면 건너뜀(도입 단계에서 검사 시작)
		const ratio = contrastRatio(fg, bg);
		const need = THRESHOLD[p.use];
		if (ratio < need) {
			const note = S3_FLOOR_PAIRS.has(`${p.fg}|${p.bg}`) ? ' (s3 하한 — 배경을 어둡게 하지 말 것, 결정 14)' : '';
			out.push({ key: `${theme}|${p.fg}|${p.bg}`, msg: `${theme} ${p.fg}(${fg}) on ${p.bg}(${bg}) ${ratio.toFixed(2)} < ${need}${note}` });
		}
	}
	return out;
}

for (const theme of ['dark', 'light']) {
	test(`토큰 대비 계약 — ${theme}`, { skip: tokens[theme] ? false : '라이트 블록 없음(A11Y 4단계에서 도입)' }, () => {
		const bad = failures(theme).filter((f) => !EXPECTED_FAIL.has(f.key));
		assert.deepEqual(bad.map((f) => f.msg), []);
		const now = new Set(failures(theme).map((f) => f.key));
		const fixed = [...EXPECTED_FAIL].filter((k) => k.startsWith(theme + '|') && !now.has(k));
		assert.deepEqual(fixed, [], 'expectedFail 인데 통과 — 목록에서 제거');
	});
}

test('라이트 블록 2개 선언 동일 · 다크 토큰 누락 없음', { skip: tokens.light ? false : '라이트 블록 없음' }, () => {
	assert.deepEqual(tokens.lightMedia, tokens.light);
	const missing = Object.keys(tokens.dark).filter((k) => k.startsWith('--color-') && !(k in tokens.light));
	assert.deepEqual(missing, []);
});
