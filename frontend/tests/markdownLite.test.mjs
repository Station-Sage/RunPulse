// frontend/src/lib/markdownLite.ts 순수 함수 테스트 — 실행: npm run test:unit
import test from 'node:test';
import assert from 'node:assert/strict';
import { parseMarkdown, stripMarkdown, localizeSource } from '../src/lib/markdownLite.ts';

// ── parseMarkdown ──

test('빈 줄은 blank 토큰을 반환한다', () => {
	const tokens = parseMarkdown('');
	assert.equal(tokens.length, 1);
	assert.equal(tokens[0].type, 'blank');
});

test('평문은 paragraph 토큰 하나를 반환한다', () => {
	const [tok] = parseMarkdown('안녕하세요');
	assert.equal(tok.type, 'paragraph');
	assert.deepEqual(tok.spans, [{ type: 'text', text: '안녕하세요' }]);
});

test('**굵게** 는 bold span 으로 파싱된다', () => {
	const [tok] = parseMarkdown('**오늘의 훈련**');
	assert.equal(tok.type, 'paragraph');
	assert.deepEqual(tok.spans, [{ type: 'bold', text: '오늘의 훈련' }]);
});

test('볼드와 평문이 섞인 문장은 여러 span 을 반환한다', () => {
	const [tok] = parseMarkdown('결과: **좋음** 입니다');
	assert.equal(tok.type, 'paragraph');
	assert.deepEqual(tok.spans, [
		{ type: 'text', text: '결과: ' },
		{ type: 'bold', text: '좋음' },
		{ type: 'text', text: ' 입니다' }
	]);
});

test('# 제목은 heading level 1 을 반환한다', () => {
	const [tok] = parseMarkdown('# 오늘의 추천');
	assert.equal(tok.type, 'heading');
	assert.equal(tok.level, 1);
	assert.deepEqual(tok.spans, [{ type: 'text', text: '오늘의 추천' }]);
});

test('### 제목은 heading level 3 을 반환한다', () => {
	const [tok] = parseMarkdown('### 세부 항목');
	assert.equal(tok.type, 'heading');
	assert.equal(tok.level, 3);
});

test('- 로 시작하는 줄은 list_item 을 반환한다', () => {
	const [tok] = parseMarkdown('- TSB -28.4 — 피로 축적');
	assert.equal(tok.type, 'list_item');
	assert.deepEqual(tok.spans, [{ type: 'text', text: 'TSB -28.4 — 피로 축적' }]);
});

test('* 로 시작하는 줄도 list_item 을 반환한다', () => {
	const [tok] = parseMarkdown('* 항목');
	assert.equal(tok.type, 'list_item');
});

test('여러 줄 파싱 순서가 유지된다', () => {
	const tokens = parseMarkdown('## 제목\n- 항목\n내용');
	assert.equal(tokens[0].type, 'heading');
	assert.equal(tokens[1].type, 'list_item');
	assert.equal(tokens[2].type, 'paragraph');
});

// ── stripMarkdown ──

test('stripMarkdown: ** 기호를 제거한다', () => {
	assert.equal(stripMarkdown('**굵게**'), '굵게');
});

test('stripMarkdown: # 헤딩 기호를 제거한다', () => {
	assert.equal(stripMarkdown('## 제목'), '제목');
});

test('stripMarkdown: 목록 기호를 제거한다', () => {
	assert.equal(stripMarkdown('- 항목'), '항목');
});

test('stripMarkdown: 줄바꿈을 공백으로 바꾼다', () => {
	assert.equal(stripMarkdown('첫 줄\n둘째 줄'), '첫 줄 둘째 줄');
});

test('stripMarkdown: 실데이터 형태의 긴 텍스트에서 별표가 제거된다', () => {
	const raw = '**"훈련 분석"에 대한 분석** - TSB(신선도): -16.5 - 피로';
	const result = stripMarkdown(raw);
	assert.ok(!result.includes('**'), `별표가 남음: ${result}`);
	assert.ok(result.startsWith('"훈련 분석"'));
});

// ── localizeSource ──

test('localizeSource: rule → 규칙 기반 답변', () => {
	assert.equal(localizeSource('rule'), '규칙 기반 답변');
});

test('localizeSource: null → null', () => {
	assert.equal(localizeSource(null), null);
});

test('localizeSource: 알 수 없는 값은 그대로 반환한다', () => {
	assert.equal(localizeSource('gpt-4o'), 'gpt-4o');
});
