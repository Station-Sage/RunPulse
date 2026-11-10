// 메트릭 상세(/library/metrics/[slug]) 순수 헬퍼 — 주소 값 검증(M-25), 선택일 타일(M-05),
// 밴드 범위 문구(M-32), 표시 단위(M-06). 테스트: frontend/tests/metricDetailC.test.mjs
import { dateError } from './wellnessDay.ts';
import { unitLabel } from './metricTabLabels.ts';
import { providerLabel } from './provider.ts';

export const DETAIL_PERIODS = [
	{ key: '4w', label: '4주' },
	{ key: '3m', label: '3개월' },
	{ key: '6m', label: '6개월' },
	{ key: '1y', label: '1년' }
] as const;

const PARAM_LABELS: Record<string, string> = { period: '기간', date: '날짜' };

/** `?period=`·`?date=` 검증. 쓸 수 없는 값은 빼고(dropped) 기본값으로 본다. */
export function parseDetailParams(sp: URLSearchParams): { period: string; date: string | null; dropped: string[] } {
	const dropped: string[] = [];
	const rawPeriod = sp.get('period');
	const period = rawPeriod && DETAIL_PERIODS.some((p) => p.key === rawPeriod) ? rawPeriod : '3m';
	if (rawPeriod != null && period !== rawPeriod) dropped.push('period');
	const rawDate = sp.get('date');
	const date = rawDate && dateError(rawDate) === null ? rawDate : null;
	if (rawDate != null && date == null) dropped.push('date');
	return { period, date, dropped };
}

/** 빼고 보여 준 주소 값 안내 한 줄('' 이면 표시 안 함). 문구는 임시(TXT-1) — 활동 목록(E-27)과 같은 말투. */
export function droppedNotice(dropped: string[]): string {
	if (!dropped.length) return '';
	return `주소의 ${dropped.map((k) => PARAM_LABELS[k] ?? k).join('·')} 값을 쓸 수 없어 빼고 보여 드려요.`;
}

/** 주소에서 빼야 할 값을 지운 search 문자열(앞 '?' 포함, 비면 ''). */
export function cleanedSearch(search: string, dropped: string[]): string {
	const sp = new URLSearchParams(search);
	for (const k of dropped) sp.delete(k);
	const qs = sp.toString();
	return qs ? `?${qs}` : '';
}

export interface Pt {
	date: string;
	value: number;
}

/**
 * M-05: 선택일(pin)이 있으면 그날 값·그날까지의 점으로 '현재/변화' 타일을 만든다.
 * pin 이 없거나 차트 범위 밖이면 최신값(pinned=false). 그날 값이 없으면 그 이전 가장 가까운 점.
 */
export function tileBasis(points: Pt[], pinned: string | null): { point: Pt | null; upto: Pt[]; pinned: boolean } {
	const last = points.at(-1) ?? null;
	if (!pinned || !last || pinned >= last.date || pinned < points[0].date) return { point: last, upto: points, pinned: false };
	const upto = points.filter((p) => p.date <= pinned);
	return { point: upto.at(-1) ?? null, upto, pinned: true };
}

/** '9월 26일' */
export function mdLabel(iso: string): string {
	return `${Number(iso.slice(5, 7))}월 ${Number(iso.slice(8, 10))}일`;
}

/** 밴드 범위 문구 — '30 미만' / '30–50' / '85 이상'(M-32: '–30'·'85–' 대신). */
export function bandRangeText(b: { from: number | null; to: number | null }, fmt: (v: number) => string = String): string {
	if (b.from == null && b.to == null) return '';
	if (b.from == null) return `${fmt(b.to as number)} 미만`;
	if (b.to == null) return `${fmt(b.from)} 이상`;
	return `${fmt(b.from)}–${fmt(b.to)}`;
}

/** 값 옆 단위(M-06·M-10): 형식이 단위를 품은 경우(%·시간·페이스) 빈 문자열, 그 외 한글 단위. */
export function metricUnitText(meta: { format?: string; unit?: string | null }, name = ''): string {
	const unit = meta.unit ?? '';
	if (!unit || unit === 'sec' || unit === 'sec/km') return '';
	if (meta.format === 'percent' || meta.format === 'duration' || meta.format === 'duration_hm' || meta.format === 'race_time' || meta.format === 'pace') return '';
	if (unit === 'brpm') return '회/분';
	return unitLabel(unit, name);
}

/** M-08: 출처 한 줄 — 'wellness' 는 웰니스 기록, 그 외 provider 이름. 없으면 ''. 문구 임시(TXT-1). */
export function sourceText(source: string | null | undefined): string {
	if (!source) return '';
	if (source === 'wellness') return '출처: 웰니스 기록(기기 동기화 값)';
	return `출처: ${providerLabel(source as Parameters<typeof providerLabel>[0])}`;
}
