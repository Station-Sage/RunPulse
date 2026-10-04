export type MeaningStatus = 'excellent' | 'good' | 'neutral' | 'caution' | 'poor';

export const STATUS_TEXT_CLASS: Record<MeaningStatus, string> = {
	excellent: 'text-semantic-green',
	good: 'text-semantic-teal',
	neutral: 'text-fg-secondary',
	caution: 'text-semantic-amber',
	poor: 'text-semantic-red'
};

export const STATUS_DOT_COLOR: Record<MeaningStatus, string> = {
	excellent: 'var(--color-semantic-green)',
	good: 'var(--color-semantic-teal)',
	neutral: 'var(--color-fg-secondary)',
	caution: 'var(--color-semantic-amber)',
	poor: 'var(--color-semantic-red)'
};

/** 스파크라인 캡션 `14일 · ▼6.2%` — 변화 없음(|%|<0.5)은 `14일 · 변동 없음`, 비교 불가면 null. */
export function sparkCaption(change: { abs: number; pct: number | null; days: number } | null | undefined): string | null {
	if (!change) return null;
	const { abs, pct, days } = change;
	const mag = pct != null ? Math.abs(pct) : null;
	if (mag != null ? mag < 0.5 : abs === 0) return `${days}일 · 변동 없음`;
	const arrow = abs > 0 ? '▲' : '▼';
	const text = mag != null ? `${mag.toFixed(mag < 10 ? 1 : 0)}%` : String(Math.round(Math.abs(abs) * 10) / 10);
	return `${days}일 · ${arrow}${text}`;
}

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
