import test from 'node:test';
import assert from 'node:assert/strict';
import { buildMetricSections, sectionConclusion, isEstimate } from '../src/lib/metricSections.ts';

const m = (name, status, confidence = null) => ({ metric_name: name, status, confidence, numeric_value: 1, text_value: null, json_value: null, provider: null, unit: '', description: name });

test('섹션 순서·미매핑 숨김', () => {
	const by = { load: [m('a', 'good')], efficiency: [m('b')], weather: [m('c')], _unmapped: [m('d')] };
	const off = buildMetricSections(by, () => true, false);
	assert.deepEqual(off.map((s) => s.key), ['load', 'efficiency', 'etc']);
	assert.equal(off[2].items.length, 1);
	assert.equal(buildMetricSections(by, () => true, true)[2].items.length, 2);
});

test('sectionConclusion', () => {
	assert.equal(sectionConclusion([m('a', 'caution'), m('b', 'good')]), '주의할 지표 1개 · 양호 1개');
	assert.equal(sectionConclusion([m('a', 'good')]), '대체로 양호 · 1개 지표');
	assert.equal(sectionConclusion([m('a')]), '1개 지표');
});

test('isEstimate', () => {
	assert.equal(isEstimate(m('a', 'good', 0.5)), true);
	assert.equal(isEstimate(m('a', 'good', 0.9)), false);
	assert.equal(isEstimate(m('a', 'good')), false);
});
