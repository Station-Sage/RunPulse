// V2-AUDIT-INDIV 묶음 C(지표·웰니스·이야기·소스 비교) 순수 헬퍼 테스트.
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { parseDetailParams, droppedNotice, cleanedSearch, tileBasis, bandRangeText, metricUnitText, sourceText, mdLabel } from '../src/lib/metricDetail.ts';
import { providerKey, providerKeys, matchesProvider, cardValue, cardUnit, WELLNESS_PROVIDER } from '../src/lib/metricListView.ts';
import { matchesMetric } from '../src/lib/metricSearch.ts';
import { dateError, dateLabel, movedNotice, fmtDur, durDelta } from '../src/lib/wellnessDay.ts';
import { niceStep, sparkAriaLabel, snapRange } from '../src/lib/trendChart.ts';
import { riskPeakText, deltaPctText, thisMonthId } from '../src/lib/storyPeriod.ts';
import { daysInvalid, signedPct, pairCountText, cellText } from '../src/lib/providerMatrix.ts';
import { formatHm, formatMetric } from '../src/lib/format.ts';

describe('metricDetail (M-05·06·25·32·08)', () => {
	it('parseDetailParams drops bad period/date', () => {
		const r = parseDetailParams(new URLSearchParams('period=zzz&date=bad&from=today'));
		assert.deepEqual(r, { period: '3m', date: null, dropped: ['period', 'date'] });
		assert.deepEqual(parseDetailParams(new URLSearchParams('period=1y&date=2026-09-26')), { period: '1y', date: '2026-09-26', dropped: [] });
		assert.deepEqual(parseDetailParams(new URLSearchParams('date=2026-02-30')).dropped, ['date']);
	});
	it('droppedNotice / cleanedSearch', () => {
		assert.equal(droppedNotice([]), '');
		assert.match(droppedNotice(['period']), /기간 값을 쓸 수 없어/);
		assert.equal(cleanedSearch('?period=zzz&from=today', ['period']), '?from=today');
		assert.equal(cleanedSearch('?period=zzz', ['period']), '');
	});
	it('tileBasis follows pin inside range, latest otherwise', () => {
		const pts = [{ date: '2026-09-01', value: 1 }, { date: '2026-09-10', value: 5 }, { date: '2026-09-20', value: 3 }];
		assert.equal(tileBasis(pts, null).pinned, false);
		const t = tileBasis(pts, '2026-09-12');
		assert.equal(t.pinned, true);
		assert.equal(t.point.value, 5);
		assert.equal(t.upto.length, 2);
		assert.equal(tileBasis(pts, '2026-09-20').pinned, false);
		assert.equal(tileBasis(pts, '2025-01-01').pinned, false);
	});
	it('bandRangeText uses 미만/이상', () => {
		assert.equal(bandRangeText({ from: null, to: 30 }), '30 미만');
		assert.equal(bandRangeText({ from: 85, to: null }), '85 이상');
		assert.equal(bandRangeText({ from: 30, to: 50 }), '30–50');
	});
	it('metricUnitText hides unit already in the value', () => {
		assert.equal(metricUnitText({ format: 'percent', unit: '%' }), '');
		assert.equal(metricUnitText({ format: 'duration_hm', unit: 'sec' }), '');
		assert.equal(metricUnitText({ format: 'number', unit: 'count' }, 'steps'), '걸음');
		assert.equal(metricUnitText({ format: 'number', unit: 'brpm' }), '회/분');
		assert.equal(metricUnitText({ format: 'number', unit: 'bpm' }), 'bpm');
	});
	it('sourceText / mdLabel', () => {
		assert.equal(sourceText(null), '');
		assert.match(sourceText('wellness'), /웰니스 기록/);
		assert.equal(sourceText('garmin'), '출처: Garmin');
		assert.equal(mdLabel('2026-09-26'), '9월 26일');
	});
});

describe('metricListView (M-06·10·13)', () => {
	const cats = [{ category: 'x', label: 'x', metrics: [{ name: 'a', provider: 'garmin:fr965' }, { name: 'b', provider: null }, { name: 'c', provider: 'runpulse' }] }];
	it('provider keys include wellness bucket last', () => {
		assert.equal(providerKey({ provider: null }), WELLNESS_PROVIDER);
		assert.deepEqual(providerKeys(cats), ['garmin', 'runpulse', WELLNESS_PROVIDER]);
		assert.equal(matchesProvider({ provider: null }, WELLNESS_PROVIDER), true);
		assert.equal(matchesProvider({ provider: 'garmin' }, 'all'), true);
		assert.equal(matchesProvider({ provider: 'garmin' }, 'runpulse'), false);
	});
	it('cardValue matches detail formatting', () => {
		assert.equal(cardValue({ name: 'rtti', value: 66, unit: '%', format: 'percent', decimal_places: 0 }), '66%');
		assert.equal(cardUnit({ name: 'rtti', value: 66, unit: '%', format: 'percent' }), '');
		assert.equal(cardValue({ name: 'acwr', value: 0.674, unit: '', format: 'number', decimal_places: 2 }), '0.67');
		assert.equal(cardValue({ name: 'steps', value: 12345, unit: 'count', format: 'number', decimal_places: 0 }), '12,345');
		assert.equal(cardValue({ name: 'x', value: null, unit: '' }), '—');
	});
});

describe('metricSearch synonyms (M-29)', () => {
	it('회복 finds utrs, vo2 finds vo2max', () => {
		assert.equal(matchesMetric({ name: 'utrs', label: 'Unified', name_ko: '훈련 준비도', abbr: 'UTRS' }, '회복'), true);
		assert.equal(matchesMetric({ name: 'vo2max', label: 'x', name_ko: '최대 산소섭취량', abbr: null }, 'VO2'), true);
		assert.equal(matchesMetric({ name: 'steps', label: 'x', name_ko: '걸음 수', abbr: null }, '회복'), false);
	});
});

describe('wellnessDay C (M-18·21·22·23·24)', () => {
	it('dateError distinguishes format vs nonexistent', () => {
		assert.equal(dateError('2026-02-30'), 'nonexistent');
		assert.equal(dateError('abc'), 'format');
		assert.equal(dateError('2026-02-28'), null);
	});
	it('dateLabel adds year when not current year', () => {
		assert.equal(dateLabel('2020-01-01', '2026-11-10'), '2020년 1월 1일 (수)');
		assert.equal(dateLabel('2026-01-01', '2026-11-10'), '1월 1일 (목)');
	});
	it('movedNotice only for future requests', () => {
		assert.equal(movedNotice(null, '2026-11-10'), null);
		assert.equal(movedNotice('2026-11-01', '2026-11-10'), null);
		assert.match(movedNotice('2030-01-01', '2026-11-10'), /2030년 1월 1일 \(화\)은 아직 오지 않은 날/);
	});
	it('fmtDur rounds minutes, durDelta matches shown values', () => {
		assert.equal(fmtDur(59 * 60 + 40), '1h 0m');
		assert.equal(durDelta(7 * 3600 + 19 * 60 + 40, 7 * 3600 + 10), '+20m');
		assert.equal(durDelta(3600, 3600 + 2 * 3600 + 47 * 60), '−2h 47m');
		assert.equal(durDelta(3600, 3600 + 20), '±0m');
	});
	it('formatHm / formatMetric duration_hm', () => {
		assert.equal(formatHm(26280), '7h 18m');
		assert.equal(formatHm(-921), '−15m');
		assert.equal(formatMetric({ format: 'duration_hm' }, 3420), '57m');
	});
});

describe('trendChart C (M-26·32)', () => {
	it('niceStep gives 1/2/5 steps and snapRange ticks are round', () => {
		assert.equal(niceStep(56.8), 20);
		assert.equal(niceStep(0.4), 0.1);
		const r = snapRange({ min: 35.2, max: 92 }, niceStep(92 - 35.2));
		assert.deepEqual(r, { min: 20, max: 100 });
		assert.equal((r.max + r.min) / 2, 60);
	});
	it('sparkAriaLabel skips nulls', () => {
		const t = sparkAriaLabel('UTRS', '30일', ['2026-10-01', '2026-10-02', '2026-10-03'], [50, null, 70]);
		assert.match(t, /UTRS 30일: 현재 70, 최고 70\(10월 3일\), 최저 50\(10월 1일\)/);
	});
});

describe('storyPeriod C (M-15·16)', () => {
	it('riskPeakText does not call safe ACWR 위험', () => {
		assert.equal(riskPeakText({ slug: 'acwr', value: 0.86, date: '2026-09-10', status: 'good', status_label: '적정' }).title, '가장 높았던 부하비');
		assert.equal(riskPeakText({ slug: 'acwr', value: 1.6, date: '2026-09-10', status: 'poor', status_label: '위험' }).title, '부하 위험 신호');
		assert.equal(riskPeakText({ slug: 'acwr', value: 0.7, date: '2026-09-10', status: 'caution', status_label: '저부하' }).title, '가장 높았던 부하비');
	});
	it('deltaPctText / thisMonthId', () => {
		assert.equal(deltaPctText(-70), '−70%');
		assert.equal(deltaPctText(0), '0%');
		assert.equal(deltaPctText(12), '+12%');
		assert.equal(thisMonthId('2026-11-10'), '2026-11');
	});
});

describe('providerMatrix C (M-19·20)', () => {
	it('daysInvalid / signedPct / pairCountText', () => {
		assert.equal(daysInvalid(null), false);
		assert.equal(daysInvalid('56'), false);
		assert.equal(daysInvalid('999'), true);
		assert.equal(signedPct(-0.3), '0%');
		assert.equal(signedPct(-12.4), '−12%');
		assert.equal(signedPct(3.24, 1), '+3.2%');
		assert.equal(pairCountText('pair_activity', 9, 17, 'Garmin↔RunPulse'), 'Garmin↔RunPulse · 러닝 17건 중 9건 비교');
		assert.equal(pairCountText('pair_daily', 9, 17, 'A↔B'), 'A↔B · 9일 비교');
	});
	it('cellText notes lagging cell', () => {
		const t = cellText({ format: 'int', unit: null }, { median: 50, latest: 50, last_date: '2026-09-27', stale: false, lagging: true, estimated: false, n: 3 });
		assert.equal(t.note, '9/27 이후 없음');
	});
});
