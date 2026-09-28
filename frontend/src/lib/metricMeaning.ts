export type MeaningStatus = 'excellent' | 'good' | 'neutral' | 'caution' | 'poor';
export interface Meaning {
	status: MeaningStatus;
	note: string;
}

export const STATUS_TEXT_CLASS: Record<MeaningStatus, string> = {
	excellent: 'text-semantic-green',
	good: 'text-semantic-teal',
	neutral: 'text-fg-secondary',
	caution: 'text-semantic-amber',
	poor: 'text-semantic-red'
};

// 등급 판정(경계값)은 서버 src/metrics/bands.py 단일 정의 — API의 status·status_label을 렌더한다.

const LABELS: Record<string, string> = {
	ctl: '체력 (CTL)',
	atl: '피로 (ATL)',
	tsb: '폼 (TSB)',
	acwr: '급성/만성 부하비 (ACWR)',
	utrs: '훈련 준비도 (UTRS)',
	cirs: '부상 위험도 (CIRS)',
	crs: '복합 준비도 (CRS)',
	rec: '러닝 효율 (REC)'
};

// 내부 식별자 "(parent: xxx)"는 사용자 화면에 노출하지 않는다.
export function displayLabel(name: string, label: string): string {
	return LABELS[name] ?? label.replace(/\s*\(parent:[^)]*\)/g, '').trim();
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
