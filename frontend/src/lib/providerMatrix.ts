// 소스 비교(S6) 표시 헬퍼 — 임계값 판단은 서버(status)가 하고 여기선 문구·링크·좌표만 만든다.
import { formatMetric } from './format.ts';
import type { ProviderCell, ProviderMatrixRow, ProviderPairItem } from './types/index.ts';

export const PERIOD_DAYS = [
	{ days: 28, label: '4주' },
	{ days: 56, label: '8주' },
	{ days: 84, label: '12주' }
] as const;

export const PROVIDER_NAMES: Record<string, string> = {
	garmin: 'Garmin',
	intervals: 'Intervals.icu',
	strava: 'Strava',
	runalyze: 'Runalyze',
	runpulse: 'RunPulse'
};

export const providerName = (p: string) => PROVIDER_NAMES[p] ?? p;

export function parseDays(raw: string | null): number {
	const n = Number(raw);
	return PERIOD_DAYS.some((p) => p.days === n) ? n : 28;
}

/** M-20: ?days= 가 있는데 쓸 수 없는 값이면 true(4주로 보고 안내·주소 정리). */
export function daysInvalid(raw: string | null): boolean {
	return raw != null && parseDays(raw) !== Number(raw);
}

/** 쓸 수 없는 기간 안내 한 줄(TXT-1 확정 문구). */
export const DAYS_NOTICE = '주소의 기간 값을 쓸 수 없어 4주로 보여 드려요.';

/** 부호 있는 % — 반올림해 0이면 '0%'('-0%' 방지), 음수는 U+2212(M-19). */
export function signedPct(v: number, dp = 0): string {
	const r = Number(v.toFixed(dp));
	if (r === 0) return `${(0).toFixed(dp)}%`;
	return `${r > 0 ? '+' : '−'}${Math.abs(r).toFixed(dp)}%`;
}

/** 차이 칸 보조 줄: 활동 쌍은 '러닝 17건 중 9건 비교', 일별 쌍은 '9일 비교'(M-19). */
export function pairCountText(kind: string, n: number, sampleN: number, label: string): string {
	const count = kind === 'pair_activity' ? `러닝 ${sampleN}건 중 ${n}건 비교` : `${n}일 비교`;
	return `${label} · ${count}`;
}

/** 행에서 값이 있는 소스 열만(매트릭스 전체 열 순서 유지). */
export function visibleProviders(all: string[], rows: ProviderMatrixRow[]): string[] {
	return all.filter((p) => rows.some((r) => p in r.cells));
}

const mmdd = (iso: string) => `${Number(iso.slice(5, 7))}/${Number(iso.slice(8, 10))}`;

/** 셀 문구: 창 안 중앙값, 없으면(stale) 최신값 + "M/D 이후 없음". */
export function cellText(row: Pick<ProviderMatrixRow, 'format' | 'unit'>, cell: ProviderCell | undefined): {
	main: string;
	note: string | null;
} {
	if (!cell) return { main: '—', note: null };
	const meta = { format: row.format === 'int' || row.format.startsWith('float') ? undefined : row.format, unit: row.unit ?? '', decimal_places: decimals(row.format) };
	if (cell.median == null) {
		return { main: formatMetric(meta, cell.latest), note: `${mmdd(cell.last_date)} 이후 없음` };
	}
	return { main: formatMetric(meta, cell.median), note: cell.stale || cell.lagging ? `${mmdd(cell.last_date)} 이후 없음` : null };
}

function decimals(format: string): number | undefined {
	if (format === 'int') return 0;
	const m = /^float(\d)$/.exec(format);
	return m ? Number(m[1]) : undefined;
}

export function rowHref(base: string, row: Pick<ProviderMatrixRow, 'href_group'>, days: number): string | null {
	return row.href_group ? `${base}/library/providers/${row.href_group}?days=${days}` : null;
}

export function periodHref(search: string, days: number): string {
	const sp = new URLSearchParams(search);
	if (days === 28) sp.delete('days');
	else sp.set('days', String(days));
	const qs = sp.toString();
	return qs ? `?${qs}` : '?';
}

export interface PairPoint {
	x: number;
	y: number;
	outlier: boolean;
	item: ProviderPairItem;
}

/** 쌍 차트 점: x=시간 순 0..1, y=diff_pct(same) 또는 ratio(scale). 날짜 오름차순. */
export function pairSeries(pairs: ProviderPairItem[], compare: 'same' | 'scale'): PairPoint[] {
	const sorted = [...pairs].sort((a, b) => a.date.localeCompare(b.date));
	const key = compare === 'scale' ? 'ratio' : 'diff_pct';
	const vals = sorted.map((p) => p[key]).filter((v): v is number => v != null);
	if (!vals.length) return [];
	const n = sorted.length;
	return sorted
		.filter((p) => p[key] != null)
		.map((p, i) => ({ x: n === 1 ? 0.5 : i / (n - 1), y: p[key] as number, outlier: p.outlier, item: p }));
}
