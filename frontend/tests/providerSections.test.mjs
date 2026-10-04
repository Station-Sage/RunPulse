import test from 'node:test';
import assert from 'node:assert/strict';
import { groupBySection, summaryLine, diffText } from '../src/lib/providerSections.ts';

const row = (slug, section, detected = false, diff = null) => ({
	slug, label: slug, unit: null, section, values: {}, diff,
	discrepancy: detected ? { detected: true } : null, preferredProvider: null, primaryReason: null
});

test('groupBySection: 순서·빈 섹션 제외·section 없으면 record', () => {
	const g = groupBySection([row('a', 'related'), row('b', undefined), row('c', 'computed')]);
	assert.deepEqual(g.map((s) => s.key), ['record', 'computed', 'related']);
	assert.equal(groupBySection([row('a', 'record')]).length, 1);
});

test('summaryLine', () => {
	assert.equal(summaryLine([row('a', 'record', true), row('b', 'related')]), '측정 차이 1건 · 정의가 달라 비교하지 않는 항목 1개');
	assert.equal(summaryLine([row('a', 'record')]), '측정 차이 없음');
});

test('diffText', () => {
	assert.deepEqual(diffText(row('a', 'record', false, { abs: 1, pct: 3.24, significant: true })), { text: '+3.2%', significant: true });
	assert.equal(diffText(row('a', 'record', false, { abs: 0, pct: 0.1, significant: false })).text, '≈');
	assert.equal(diffText(row('a', 'related')).text, '');
});
