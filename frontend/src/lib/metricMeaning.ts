export type MeaningStatus = 'excellent' | 'good' | 'neutral' | 'caution' | 'poor';

export const STATUS_TEXT_CLASS: Record<MeaningStatus, string> = {
	excellent: 'text-semantic-green',
	good: 'text-semantic-teal',
	neutral: 'text-fg-secondary',
	caution: 'text-semantic-amber',
	poor: 'text-semantic-red'
};

// 등급 판정(경계값)은 서버 src/metrics/bands.py 단일 정의 — API의 status·status_label을 렌더한다.

// 서버가 내려준 name_ko·abbr로 표시명을 만든다(하드코딩 없음).
export function displayLabel(m: { name_ko: string; abbr?: string | null }): string {
	return m.abbr ? `${m.name_ko} (${m.abbr})` : m.name_ko;
}

// UTRS/CIRS 구성요소 같은 하위 메트릭 — 그리드에서는 숨기고 상위 메트릭의 분해 시트에서 본다.
export function isComponentMetric(label: string): boolean {
	return /\(parent:/.test(label);
}

// 값이 전부 같은 스파크라인은 정보가 없다(캡 걸린 값·미계산 가능성).
export function isFlat(series: (number | null)[]): boolean {
	const v = series.filter((x): x is number => x != null);
	return v.length >= 2 && v.every((x) => x === v[0]);
}
