import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { matchesMetric } from '../src/lib/metricSearch.ts';

const m = { name: 'race_pred_marathon_sec', label: 'Marathon', name_ko: '마라톤 예측', abbr: null };
describe('matchesMetric', () => {
	it('빈 검색어는 전부 일치', () => assert.equal(matchesMetric(m, '  '), true));
	it('한글명 부분 일치', () => assert.equal(matchesMetric(m, '예측'), true));
	it('slug·라벨 대소문자 무시', () => {
		assert.equal(matchesMetric(m, 'MARATHON'), true);
		assert.equal(matchesMetric(m, 'pred_marathon'), true);
	});
	it('약어 일치·불일치', () => {
		assert.equal(matchesMetric({ ...m, abbr: 'UTRS' }, 'utr'), true);
		assert.equal(matchesMetric(m, 'ctl'), false);
	});
});
