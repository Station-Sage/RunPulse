import test from 'node:test';
import assert from 'node:assert/strict';
import { isSmallData, lockedRows } from '../src/lib/unlock.ts';

const e = (have, req, basis = 'load_span') => ({ required_days: req, have_days: have, unlocked: have >= req, basis });
const map = (o = {}) => ({ ctl: e(50, 42), tsb: e(50, 42), cirs: e(50, 28), utrs: e(10, 7, 'wellness_days'), ...o });

test('모두 열리면 적은 데이터가 아니다', () => {
	assert.equal(isSmallData(map()), false);
	assert.deepEqual(lockedRows(map()), []);
});

test('코어 게이지 하나라도 잠기면 적은 데이터', () => {
	assert.equal(isSmallData(map({ tsb: e(10, 42) })), true);
});

test('null 이면 판정하지 않는다', () => {
	assert.equal(isSmallData(null), false);
	assert.deepEqual(lockedRows(undefined), []);
});

test('진행률과 안내 문구', () => {
	const rows = lockedRows(map({ tsb: e(21, 42), utrs: e(0, 7, 'wellness_days') }));
	const tsb = rows.find((r) => r.key === 'tsb');
	assert.equal(tsb.pct, 50);
	assert.match(tsb.hint, /21일 더/);
	assert.match(rows.find((r) => r.key === 'utrs').hint, /들어오면/);
});

import { lockedMetricNotice } from '../src/lib/unlock.ts';
test('지표 상세 잠금 안내', () => {
	const u = { ctl: { required_days: 42, have_days: 28, unlocked: false, basis: 'load_span' }, tsb: { required_days: 42, have_days: 50, unlocked: true, basis: 'load_span' }, cirs: { required_days: 28, have_days: 1, unlocked: false, basis: 'load_span' }, utrs: { required_days: 7, have_days: 9, unlocked: true, basis: 'wellness_days' } };
	assert.equal(lockedMetricNotice('ctl', u).message, '이 지표는 42일 데이터가 필요해요 · 지금 28일');
	assert.match(lockedMetricNotice('ctl', u).formula, /42일/);
	assert.equal(lockedMetricNotice('tsb', u), null);
	assert.equal(lockedMetricNotice('pace', u), null);
	assert.equal(lockedMetricNotice('ctl', null), null);
});
