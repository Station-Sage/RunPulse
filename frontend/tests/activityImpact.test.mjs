// 문장 조립은 서버(activity_impact_wording.impact_lines, tests/test_activity_impact_wording.py)로 옮겼다.
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { impactView } from '../src/lib/activityImpact.ts';

describe('impactView', () => {
	const lines = ['이 날 체력(CTL) +2.3 · 폼(TSB) +5', '서울마라톤 D-30에 쌓은 세션'];

	it('rule → 서버 줄 그대로, AI 없음', () => {
		assert.deepEqual(impactView({ lines, wording: { text: lines.join(' / '), source: 'rule' } }), { lines, ai: null });
	});

	it('ai → AI 요약 + 규칙 줄 유지', () => {
		const v = impactView({ lines, wording: { text: '대회 30일 전 체력을 쌓은 러닝이에요.', source: 'ai' } });
		assert.equal(v.ai, '대회 30일 전 체력을 쌓은 러닝이에요.');
		assert.deepEqual(v.lines, lines);
	});

	it('lines 없음·null → 빈 목록', () => {
		assert.deepEqual(impactView(null), { lines: [], ai: null });
		assert.deepEqual(impactView({}), { lines: [], ai: null });
	});
});
