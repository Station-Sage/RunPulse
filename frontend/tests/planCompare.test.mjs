import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildCompareRows, isRecommended, riskClass } from '../src/lib/planCompare.ts';

const t = (o) => ({ weeks: 12, label: '권장', weekly_km_target: 60, achievability_pct: 70, projected_time_end: 11940, risk_level: '낮음', status_summary: '', ...o });

test('only differing rows are flagged', () => {
	const rows = buildCompareRows([t({}), t({ weeks: 16, label: '여유형', weekly_km_target: 55 })]);
	const by = Object.fromEntries(rows.map((r) => [r.key, r]));
	assert.equal(by.weeks.differs, true);
	assert.equal(by.km.differs, true);
	assert.equal(by.ach.differs, false);
	assert.equal(by.time.cells[0], '3:19:00');
});

test('null values render dash and risk colors', () => {
	const rows = buildCompareRows([t({ weekly_km_target: null, projected_time_end: null, risk_level: null })]);
	assert.equal(rows.find((r) => r.key === 'km').cells[0], '—');
	assert.equal(riskClass('높음'), 'text-semantic-red');
	assert.equal(riskClass('중간'), 'text-semantic-amber');
	assert.equal(riskClass(null), 'text-fg-muted');
	assert.equal(isRecommended(t({})), true);
});
