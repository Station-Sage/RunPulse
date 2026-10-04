import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
	monthRange,
	presetRange,
	recentMonths,
	parseFilters,
	serializeFilters
} from '../src/lib/activityFilters.ts';

const TODAY = '2026-10-04';
const parse = (qs) => parseFilters(new URLSearchParams(qs), TODAY);

test('monthRange: 말일 계산(2월·윤년·12월)', () => {
	assert.deepEqual(monthRange('2026-02'), { from: '2026-02-01', to: '2026-02-28' });
	assert.deepEqual(monthRange('2024-02'), { from: '2024-02-01', to: '2024-02-29' });
	assert.deepEqual(monthRange('2026-12'), { from: '2026-12-01', to: '2026-12-31' });
});

test('presetRange: 최근 30일은 오늘 포함 30일', () => {
	assert.deepEqual(presetRange('30d', TODAY), { from: '2026-09-05', to: TODAY });
	assert.deepEqual(presetRange('month', TODAY), { from: '2026-10-01', to: TODAY });
	assert.deepEqual(presetRange('year', TODAY), { from: '2026-01-01', to: TODAY });
	assert.deepEqual(presetRange('all', TODAY), {});
});

test('recentMonths: 연도 경계', () => {
	assert.deepEqual(recentMonths('2026-02-10', 4), ['2026-02', '2026-01', '2025-12', '2025-11']);
});

test('parseFilters: 빈 쿼리는 전체 기간', () => {
	const s = parse('');
	assert.equal(s.preset, 'all');
	assert.equal(s.from, undefined);
	assert.equal(s.sport, '');
});

test('parseFilters: month가 from/to보다 우선, 잘못된 값은 무시', () => {
	const s = parse('month=2026-09&from=2020-01-01');
	assert.equal(s.from, '2026-09-01');
	assert.equal(s.to, '2026-09-30');
	assert.equal(s.preset, null);
	assert.equal(parse('month=2026-13').preset, 'all');
	assert.equal(parse('from=abc').from, undefined);
});

test('parseFilters: 직접 from/to(과거 링크)는 유지', () => {
	const s = parse('from=2026-09-01&to=2026-09-30&sport=running&dist_min=10&q=long');
	assert.equal(s.preset, null);
	assert.equal(s.from, '2026-09-01');
	assert.equal(s.sport, 'running');
	assert.equal(s.distMin, '10');
	assert.equal(s.q, 'long');
});

test('serializeFilters: 기본값 생략·왕복 일치', () => {
	assert.equal(serializeFilters(parse('')), '');
	for (const qs of ['period=30d', 'month=2026-09&sport=running', 'from=2026-09-01&to=2026-09-30&q=a', 'dist_min=21.1']) {
		const once = serializeFilters(parse(qs));
		assert.equal(serializeFilters(parse(once.slice(1))), once);
	}
	assert.equal(serializeFilters(parse('period=year&sport=running')), '?period=year&sport=running');
});

test('type/sort 왕복 — sort=date 는 생략', () => {
	const s = parse('type=long&sort=load&sport=running');
	assert.equal(s.type, 'long');
	assert.equal(s.sort, 'load');
	assert.equal(serializeFilters(s), '?sport=running&type=long&sort=load');
	assert.equal(serializeFilters(parse('sort=date')), '');
	assert.equal(parse('sort=bogus').sort, '');
});
