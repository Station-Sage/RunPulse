// frontend/src/lib/predictionCompare.ts
// 레이스 예측 3경로 비교 표시용 순수 함수(P7-PRED-72). 테스트: frontend/tests/predictionCompare.test.mjs

export interface CompareRow {
	key: 'garmin' | 'ref' | 'self' | 'r4' | 'r4_asym';
	label: string;
	provider: string;
	value_sec: number | null;
	as_of?: string;
	stale_days?: number;
	low_sec?: number | null;
	high_sec?: number | null;
	confidence?: number | null;
	reasons?: string[];
	contributions?: Record<string, number> | null;
	candidate?: boolean; // r4 섀도 후보(기본 표시 아님)
}

/** 초 → 'h:mm:ss' 또는 'm:ss'. */
export function clock(sec: number): string {
	const s = Math.round(sec);
	const h = Math.floor(s / 3600);
	const m = Math.floor((s % 3600) / 60);
	const r = s % 60;
	const mm = h > 0 ? String(m).padStart(2, '0') : String(m);
	return (h > 0 ? `${h}:` : '') + `${mm}:${String(r).padStart(2, '0')}`;
}

/** 80% 범위 문구. 둘 중 하나라도 없으면 null. */
export function rangeLabel(row: CompareRow): string | null {
	if (row.low_sec == null || row.high_sec == null) return null;
	return `${clock(row.low_sec)}~${clock(row.high_sec)}`;
}

/** 신뢰도 0~1 → 3단계. ≥0.7 높음, ≥0.45 보통, 그 외 낮음. null이면 null. */
export function confidenceLabel(c: number | null | undefined): '높음' | '보통' | '낮음' | null {
	if (c == null) return null;
	if (c >= 0.7) return '높음';
	if (c >= 0.45) return '보통';
	return '낮음';
}

/** 자체 추정 대비 차이(%) 문구 — 기준 행이나 대상 값이 없으면 null. 양수 = 느림. */
export function diffVsSelf(row: CompareRow, self: CompareRow | undefined): string | null {
	if (!self?.value_sec || !row.value_sec || row.key === 'self') return null;
	const pct = (row.value_sec / self.value_sec - 1) * 100;
	if (Math.abs(pct) < 0.05) return '같음';
	return `${pct > 0 ? '+' : '−'}${Math.abs(pct).toFixed(1)}%`;
}

/** 기여도 키(칼만 이득 분해, REVIEW-09 §5) → 표시 이름. 순서 = 표시 순서. */
export const CONTRIBUTION_LABELS: [string, string][] = [
	['race', '대회'],
	['paced', '최대 이하 대회'],
	['work', '작업 블록'],
	['hr', '심박'],
	['best_effort', '5K 구간 기록'],
	['T', '역치 세트'],
	['I', '인터벌 세트'],
	['R', '반복 세트'],
	['M', '마라톤 구간'],
	['H', '심박']
];

/** 기여도 → '대회 28 · 역치 세트 32 · 인터벌 세트 19 · 심박 21' (1% 미만 생략). */
export function contributionLabel(c: CompareRow['contributions']): string | null {
	if (!c) return null;
	const parts = CONTRIBUTION_LABELS.filter(([k]) => (c[k] ?? 0) >= 0.005).map(([k, l]) => `${l} ${Math.round((c[k] ?? 0) * 100)}`);
	return parts.length ? parts.join(' · ') : null;
}
