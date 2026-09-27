import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { staleLabel } from '../src/lib/threadAge.ts';

const nowMs = Date.parse('2026-09-25T00:00:00Z');

describe('staleLabel', () => {
	it('14일 전 → 당시 기준 레이블', () => {
		assert.equal(staleLabel('2026-09-10 10:00:00', nowMs), '14일 전 대화 · 당시 기준');
	});

	it('1일 전 → null', () => {
		assert.equal(staleLabel('2026-09-24 10:00:00', nowMs), null);
	});

	it('null → null', () => {
		assert.equal(staleLabel(null, nowMs), null);
	});

	it('잘못된 문자열 → null', () => {
		assert.equal(staleLabel('not-a-date', nowMs), null);
	});
});

import { threadTitles } from '../src/lib/threadAge.ts';

describe('threadTitles', () => { it('같은 제목만 날짜로 구분', () => {
	const m = threadTitles([
		{ id: 1, title: '오늘 훈련 조언', created_at: '2026-09-26T05:00:00Z' },
		{ id: 2, title: '오늘 훈련 조언', created_at: '2026-09-24T05:00:00Z' },
		{ id: 3, title: '훈련 분석', created_at: '2026-09-25T05:00:00Z' }
	]);
	assert.match(m.get(1), /^오늘 훈련 조언 · \d+\/\d+$/);
	assert.notEqual(m.get(1), m.get(2));
	assert.equal(m.get(3), '훈련 분석');
}); });
