// A11Y-L 4단계 — ChartScrub aria-valuetext(R2)·BaselineRow inlineConfirm(R1) 정적 가드.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const rd = (p) => readFileSync(new URL(`../src/lib/components/${p}`, import.meta.url), 'utf8');

test('ChartScrub 은 valueText 를 aria-valuetext 로 노출한다', () => {
	assert.match(rd('ChartScrub.svelte'), /aria-valuetext=\{[^}]*valueText/);
});

for (const f of ['TrendChart', 'FormChart', 'Sparkline', 'ActivityTimeline']) {
	test(`${f} 는 ChartScrub 에 valueText 를 넘긴다`, () => {
		assert.match(rd(`${f}.svelte`), /<ChartScrub[^>]*valueText/s);
	});
}

test('BaselineRow 확인 블록은 inlineConfirm + group', () => {
	const s = rd('data/BaselineRow.svelte');
	assert.match(s, /use:inlineConfirm/);
	assert.match(s, /role="group"/);
});
