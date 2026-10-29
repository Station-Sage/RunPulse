// A11Y 공통 1단계 — 허용 색 조합 표(accessibility-common.md §2.6 원본). 표에 없는 조합은 사용 금지.
export type PairUse = 'text' | 'large' | 'ui';
export interface Pair {
	fg: string;
	bg: string;
	use: PairUse;
	themes?: ('dark' | 'light')[];
}

export const THRESHOLD: Record<PairUse, number> = { text: 4.5, large: 3.0, ui: 3.0 };

const S1 = 'surface-1';
const S2 = 'surface-2';
const S3 = 'surface-3';

function on(fg: string, bgs: string[], use: PairUse, themes?: Pair['themes']): Pair[] {
	return bgs.map((bg) => ({ fg, bg, use, ...(themes ? { themes } : {}) }));
}

export const PAIRS: Pair[] = [
	...on('fg-primary', [S1, S2, S3], 'text'),
	...on('fg-secondary', [S1, S2], 'text'),
	...on('fg-secondary', [S3], 'large', ['dark']),
	...on('fg-secondary', [S3], 'text', ['light']),
	...on('fg-muted', [S1, S2], 'text'),
	...on('fg-muted', [S3], 'text', ['light']),
	...on('semantic-red', [S1, S2], 'text'),
	...on('semantic-red', [S3], 'ui', ['dark']),
	...on('semantic-red', [S3], 'text', ['light']),
	...on('semantic-amber', [S1, S2, S3], 'text'),
	...on('semantic-green', [S1, S2, S3], 'text'),
	...on('semantic-teal', [S1, S2], 'text'),
	...on('semantic-teal', [S3], 'ui', ['dark']),
	...on('semantic-teal', [S3], 'text', ['light']),
	...on('delta-better', [S1, S2], 'text'),
	...on('delta-worse', [S1, S2], 'text'),
	...on('delta-better', [S3], 'text', ['light']),
	...on('delta-worse', [S3], 'text', ['light']),
	...on('series-1', [S1, S2, S3], 'ui'),
	...on('series-2', [S1, S2, S3], 'ui'),
	...on('series-3', [S1, S2, S3], 'ui'),
	...on('border-strong', [S1, S2], 'ui'),
	...on('border-strong', [S3], 'ui', ['light']),
	...on('focus-ring', [S1, S2, S3], 'ui')
];

// 라이트 s3 하한 — 배경을 더 어둡게 하면 안 되는 여유 0.15 이하 조합(결정 14).
export const S3_FLOOR_PAIRS = new Set([
	'semantic-teal|surface-3',
	'series-3|surface-3',
	'border-strong|surface-3',
	'provider-strava-mark|surface-3',
	'provider-runalyze-mark|surface-3'
]);
