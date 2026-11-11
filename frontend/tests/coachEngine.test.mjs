import { test } from 'node:test';
import assert from 'node:assert/strict';
import { reasonText, needsConsent, engineLineText, bannerFor, visibleScope } from '../src/lib/coachEngine.ts';

const llm = (consent) => ({
	mode: 'llm',
	selected: { provider: 'gemini', model: 'gemini-2.5-flash' },
	chain: [{ provider: 'gemini', model: 'gemini-2.5-flash' }],
	health: { consecutive_failures: 0, last_ok_at: null, last_error: null, degraded: false },
	consent,
	scope: []
});

test('reasonText: 코드 → 한국어, 미지 코드는 원문', () => {
	assert.equal(reasonText('http_404'), '연결 실패(404)');
	assert.equal(reasonText('weird'), 'weird');
	assert.equal(reasonText(null), '알 수 없음');
});

test('needsConsent: 동의 없음/다른 provider면 true, 규칙 모드는 false', () => {
	assert.equal(needsConsent(null), false);
	assert.equal(needsConsent(llm(null)), true);
	assert.equal(needsConsent(llm({ provider: 'groq' })), true);
	assert.equal(needsConsent(llm({ provider: 'gemini' })), false);
	assert.equal(needsConsent({ ...llm(null), mode: 'rule_only' }), false);
});

test('engineLineText: 모드별 문구', () => {
	assert.equal(engineLineText({ ...llm(null), mode: 'rule_by_choice' }), '답변 엔진: 규칙 (AI 끔)');
	assert.equal(engineLineText({ ...llm(null), mode: 'rule_only' }), '답변 엔진: 규칙 (AI 미설정)');
	assert.match(engineLineText(llm({ provider: 'gemini' })), /gemini · gemini-2.5-flash$/);
	assert.match(engineLineText(llm(null)), /동의 필요/);
});

test('bannerFor: fallback/rule_only/error/cancelled만 배너', () => {
	assert.equal(bannerFor({ status: 'fallback' }), 'fallback');
	assert.equal(bannerFor({ status: 'rule_only' }), 'rule_only');
	assert.equal(bannerFor({ status: 'error' }), 'error');
	assert.equal(bannerFor({ status: 'cancelled' }), 'cancelled');
	assert.equal(bannerFor({ status: 'ok' }), null);
	assert.equal(bannerFor(undefined), null);
});

test('visibleScope: 메모 제외 시 optional 항목 제거', () => {
	const scope = [{ item: 'a', period: 'x', optional: false }, { item: 'memo', period: 'x', optional: true }];
	assert.equal(visibleScope(scope, false).length, 2);
	assert.deepEqual(visibleScope(scope, true).map((s) => s.item), ['a']);
});

test('fallbackText: 사용량 한도는 한도 안내, 그 외는 실패 문구', async () => {
	const { fallbackText, reasonText } = await import('../src/lib/coachEngine.ts');
	assert.equal(fallbackText('quota_user'), '오늘 AI 사용 한도에 도달해 규칙 답변으로 대신했어요(자정 초기화)');
	assert.match(fallbackText('quota_global'), /일시적으로 제한/);
	assert.match(fallbackText('busy'), /몰려/);
	assert.equal(fallbackText('http_404'), 'AI 연결에 실패해 규칙 답변으로 대신했어요 · 연결 실패(404)');
	assert.equal(reasonText('quota_user'), '오늘 AI 사용 한도');
	assert.equal(reasonText('http_4xx'), '요청 거부(4xx)'); // S4-88
});

test('attemptLines: 실제 시도 순서·사유, attempts 없으면 추정 한 줄 (S4-87)', async () => {
	const { attemptLines } = await import('../src/lib/coachEngine.ts');
	assert.deepEqual(
		attemptLines(
			[
				{ provider: 'openai', model: 'gpt-4o-mini', ok: false, reason: 'network' },
				{ provider: 'gemini', model: null, ok: false, reason: 'http_5xx' }
			],
			{ provider: 'claude', model: 'x' }
		),
		['OpenAI · gpt-4o-mini — 네트워크 오류', 'Gemini — 서버 오류(5xx)']
	);
	assert.deepEqual(attemptLines([{ provider: 'gemini', model: 'g', ok: true, reason: null }], null), ['Gemini · g — 성공']);
	assert.deepEqual(attemptLines(undefined, { provider: 'openai', model: 'm' }), ['OpenAI · m']);
	assert.deepEqual(attemptLines([], null), []);
});

test('hasFailedRetry: 성공 답변 중 앞선 실패가 있을 때만 (S4-88)', async () => {
	const { hasFailedRetry } = await import('../src/lib/coachEngine.ts');
	const fail = { provider: 'gemini', model: null, ok: false, reason: 'http_429' };
	const ok = { provider: 'groq', model: null, ok: true, reason: null };
	assert.equal(hasFailedRetry({ status: 'ok', attempts: [fail, ok] }), true);
	assert.equal(hasFailedRetry({ status: 'ok', attempts: [ok] }), false);
	assert.equal(hasFailedRetry({ status: 'ok' }), false); // 옛 메시지(attempts 없음)
	assert.equal(hasFailedRetry({ status: 'fallback', attempts: [fail] }), false); // 폴백은 배너의 '원인 보기'
	assert.equal(hasFailedRetry(undefined), false);
});
