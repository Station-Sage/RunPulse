// 웰니스 /:date 순수 헬퍼 — 날짜 검증·표시·수면 단계 비율. 임계값은 두지 않는다(status는 서버).
export const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

export function isValidDate(s: string): boolean {
	return dateError(s) === null;
}

/** M-24: 'format'(YYYY-MM-DD 아님) / 'nonexistent'(형식은 맞지만 없는 날, 2026-02-30) / null(정상). */
export function dateError(s: string): 'format' | 'nonexistent' | null {
	if (!DATE_RE.test(s)) return 'format';
	const d = new Date(`${s}T00:00:00Z`);
	return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === s ? null : 'nonexistent';
}

/** 오류 화면 문구(M-24) — 임시 문구(TXT-1). */
export const DATE_ERROR_TEXT = {
	format: { title: '날짜 형식이 올바르지 않아요', body: 'YYYY-MM-DD 형식의 날짜만 볼 수 있어요.' },
	nonexistent: { title: '없는 날짜예요', body: '달력에 없는 날이에요. 날짜를 다시 확인해 주세요.' }
} as const;

/** '2026-10-04' → '10월 4일 (일)'. today와 연도가 다르면 앞에 연도('2020년 1월 1일 (수)', M-18). */
export function dateLabel(s: string, today: string = localToday()): string {
	const d = new Date(`${s}T00:00:00Z`);
	const wd = ['일', '월', '화', '수', '목', '금', '토'][d.getUTCDay()];
	const year = s.slice(0, 4) !== today.slice(0, 4) ? `${d.getUTCFullYear()}년 ` : '';
	return `${year}${d.getUTCMonth() + 1}월 ${d.getUTCDate()}일 (${wd})`;
}

/** 보는 사람 기기 기준 오늘 'YYYY-MM-DD'. */
export function localToday(): string {
	return new Date().toLocaleDateString('sv-SE');
}

/** M-23: 미래 날짜를 오늘로 옮겼을 때 안내 한 줄(임시 문구, TXT-1). 옮기지 않았으면 null. */
export function movedNotice(requested: string | null, shown: string): string | null {
	if (!requested || requested === shown || requested < shown) return null;
	return `${dateLabel(requested, shown)}은 아직 오지 않은 날이라 오늘 기록을 보여 드려요.`;
}

export function shiftDate(s: string, n: number): string {
	const d = new Date(`${s}T00:00:00Z`);
	d.setUTCDate(d.getUTCDate() + n);
	return d.toISOString().slice(0, 10);
}

/** 초 → '7h 12m' / '45m'(분 반올림, M-22). null이면 '—'. */
export function fmtDur(sec: number | null | undefined): string {
	if (sec == null) return '—';
	const total = Math.round(sec / 60);
	const h = Math.floor(total / 60);
	const m = total % 60;
	return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

/** 수면 시간 − 평균, 둘 다 분으로 반올림한 뒤 뺀다(표시된 두 값의 차와 항상 같게, M-22). '+20m'/'−2h 47m'/'±0m'. */
export function durDelta(sec: number, meanSec: number): string {
	const d = Math.round(sec / 60) - Math.round(meanSec / 60);
	if (d === 0) return '±0m';
	return `${d > 0 ? '+' : '−'}${fmtDur(Math.abs(d) * 60)}`;
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
