// 웰니스 /:date 순수 헬퍼 — 날짜 검증·표시·수면 단계 비율. 임계값은 두지 않는다(status는 서버).
export const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

export function isValidDate(s: string): boolean {
	if (!DATE_RE.test(s)) return false;
	const d = new Date(`${s}T00:00:00Z`);
	return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === s;
}

/** '2026-10-04' → '10월 4일 (일)' */
export function dateLabel(s: string): string {
	const d = new Date(`${s}T00:00:00Z`);
	const wd = ['일', '월', '화', '수', '목', '금', '토'][d.getUTCDay()];
	return `${d.getUTCMonth() + 1}월 ${d.getUTCDate()}일 (${wd})`;
}

export function shiftDate(s: string, n: number): string {
	const d = new Date(`${s}T00:00:00Z`);
	d.setUTCDate(d.getUTCDate() + n);
	return d.toISOString().slice(0, 10);
}

/** 초 → '7h 12m' / '45m'. null이면 '—'. */
export function fmtDur(sec: number | null | undefined): string {
	if (sec == null) return '—';
	const h = Math.floor(sec / 3600);
	const m = Math.floor((sec % 3600) / 60);
	return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export const STAGE_LABEL: Record<string, string> = { deep: '깊은', light: '얕은', rem: 'REM', awake: '깸' };

export interface StageSeg {
	key: string;
	label: string;
	sec: number;
	pct: number;
}

/** 단계별 초 → 비율 세그먼트. 합계가 0이거나 전부 null이면 빈 배열. */
export function stageSegments(
	stages: Record<string, number | null> | null | undefined
): StageSeg[] {
	if (!stages) return [];
	const keys = ['deep', 'light', 'rem', 'awake'];
	const total = keys.reduce((a, k) => a + (stages[k] ?? 0), 0);
	if (total <= 0) return [];
	return keys
		.filter((k) => (stages[k] ?? 0) > 0)
		.map((k) => ({ key: k, label: STAGE_LABEL[k], sec: stages[k] as number, pct: ((stages[k] as number) / total) * 100 }));
}

/** 기준선 수집 진행 문구. n<7이면 '기준선 수집 중 (n/7일)'. */
export function baselineNote(n: number | null | undefined): string | null {
	if (n == null) return null;
	return n < 7 ? `기준선 수집 중 (${n}/7일)` : null;
}
