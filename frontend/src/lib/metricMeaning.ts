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

// cuts: [상한(미만), 상태, 문구] 순서대로 검사, 모두 넘으면 last
function band(v: number, cuts: [number, MeaningStatus, string][], last: [MeaningStatus, string]): Meaning {
	for (const [max, status, note] of cuts) if (v < max) return { status, note };
	return { status: last[0], note: last[1] };
}

// 개인 기준선 없이 말할 수 있는 것만 해석한다 — 근거 없는 라벨을 붙이지 않는다(원칙 1).
export function meaningFor(name: string, value: number | null | undefined): Meaning | null {
	if (value == null || !Number.isFinite(value)) return null;
	switch (name) {
		case 'tsb':
			return band(value, [[-20, 'poor', '과부하'], [-10, 'caution', '피로 누적'], [5, 'neutral', '균형'], [25, 'excellent', '레이스 최적']], ['caution', '휴식 과다']);
		case 'utrs':
		case 'crs':
			return band(value, [[40, 'poor', '낮음'], [60, 'neutral', '보통'], [80, 'good', '좋음']], ['excellent', '매우 좋음']);
		case 'cirs':
			return band(value, [[30, 'good', '낮음'], [50, 'neutral', '보통'], [70, 'caution', '주의']], ['poor', '높음']);
		case 'acwr':
			return band(value, [[0.8, 'caution', '저부하'], [1.3, 'good', '적정'], [1.5, 'caution', '주의']], ['poor', '위험']);
		case 'training_effect_aerobic':
		case 'training_effect_anaerobic':
			return band(value, [[1, 'neutral', '효과 미미'], [2, 'neutral', '체력 유지'], [3, 'good', '체력 개선'], [4, 'excellent', '큰 개선'], [5, 'caution', '매우 높은 자극']], ['poor', '과도한 자극']);
		case 'aerobic_decoupling':
		case 'aerobic_decoupling_rp':
			return band(Math.abs(value), [[5, 'excellent', '유산소 안정'], [8, 'good', '양호'], [10, 'neutral', '보통']], ['caution', '심박 드리프트']);
		default:
			return null;
	}
}

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
