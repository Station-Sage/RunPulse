import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (p) => readFileSync(new URL(`../src/${p}`, import.meta.url), 'utf8');

test('규칙 선택 모드면 코치 탭에 안내 배너를 띄운다', () => {
	const s = read('lib/components/coach/DegradedBanner.svelte');
	assert.match(s, /rule_by_choice/);
	assert.match(s, /data-testid="rule-mode-banner"/);
});

test('상세 분석 카드는 시작 버튼만 두고 코치 스레드로 이동한다', () => {
	const s = read('lib/components/coach/DeepAnalysisCard.svelte');
	assert.match(s, /startDeepAnalysis/);
	assert.match(s, /goto\(`\$\{base\}\/coach\/\$\{res\.thread\.id\}/);
	assert.doesNotMatch(s, /onAsk/);
});

test('설정 화면에 2·3순위 폴백 선택이 있다', () => {
	const s = read('routes/data/settings/ai/+page.svelte');
	assert.match(s, /data-testid="fallback-order"/);
});
