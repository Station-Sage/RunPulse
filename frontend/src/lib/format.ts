export function formatDistance(m: number): string {
	return `${(m / 1000).toFixed(1)}km`;
}

export function formatDuration(sec: number): string {
	const h = Math.floor(sec / 3600);
	const m = Math.floor((sec % 3600) / 60);
	const s = Math.floor(sec % 60);
	const mm = String(m).padStart(2, '0');
	const ss = String(s).padStart(2, '0');
	return h > 0 ? `${h}:${mm}:${ss}` : `${m}:${ss}`;
}

export function formatPace(secPerKm: number): string {
	const min = Math.floor(secPerKm / 60);
	const sec = Math.round(secPerKm % 60);
	return `${min}:${String(sec).padStart(2, '0')}/km`;
}

/**
 * 원시 단위 값을 러너가 읽을 수 있는 표현으로 변환.
 * - sec   → h:mm:ss / m:ss 형식, unit ''
 * - sec/km → m:ss/km 형식, unit ''
 * - m (≥1000) → km 1자리, unit 'km'
 * - 그 외: 100 이상은 정수, 미만은 소수 1자리, unit 그대로
 */
/** 계획 페이스 범위(초/km, min=빠른 쪽) → '6:05–6:45/km'. 한쪽만 있으면 '>6:05/km'·'<6:45/km', 둘 다 없으면 ''. */
export function formatPaceRange(min: number | null, max: number | null): string {
	if (min == null && max == null) return '';
	const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`;
	if (min != null && max != null) return `${fmt(min)}–${fmt(max)}/km`;
	return min != null ? `>${fmt(min)}/km` : `<${fmt(max!)}/km`;
}

/** 계획 진행 라벨: '3주차 / 9주', 시작 전이면 '시작 전 (2주 뒤)'. planWeeks 없으면 '3주차'. */
export function weekProgressLabel(weekIndex: number, planWeeks?: number | null): string {
	if (weekIndex < 1) return `시작 전 (${1 - weekIndex}주 뒤)`;
	return planWeeks ? `${weekIndex}주차 / ${planWeeks}주` : `${weekIndex}주차`;
}

export function formatUnitValue(value: number, unit: string): { display: string; unit: string } {
	if (unit === 'sec') {
		return { display: formatDuration(value), unit: '' };
	}
	if (unit === 'sec/km') {
		return { display: formatPace(value), unit: '' };
	}
	if (unit === 'm' && value >= 1000) {
		return { display: (value / 1000).toFixed(1), unit: 'km' };
	}
	// 정수는 그대로(58 → '58', '58.0' 아님), 100 이상은 정수, 그 외 소수 1자리(끝 0 제거) — 부동소수 잡음(26.0799…)도 여기서 정리
	const display = Number.isInteger(value)
		? String(value)
		: Math.abs(value) >= 100
			? String(Math.round(value))
			: String(Number(value.toFixed(1)));
	return { display, unit };
}

export function formatDate(isoStr: string): string {
	return isoStr.slice(0, 10);
}

// SQLite datetime('now')는 UTC인데 'YYYY-MM-DD HH:MM:SS'로 시간대 표기가 없어 JS가 로컬 시각으로
// 잘못 해석한다(KST면 9시간 어긋남). 시간대 표기가 없으면 UTC로 간주해 파싱한다.
export function parseDbTimestamp(s: string): Date {
	const hasZone = /(Z|[+-]\d{2}:?\d{2})$/.test(s);
	return new Date(hasZone ? s : s.replace(' ', 'T') + 'Z');
}

export function formatRelativeTime(isoStr: string): string {
	const diff = Date.now() - parseDbTimestamp(isoStr).getTime();
	const minutes = Math.floor(diff / 60_000);
	if (minutes < 2) return '방금 전';
	if (minutes < 60) return `${minutes}분 전`;
	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${hours}시간 전`;
	const days = Math.floor(hours / 24);
	if (days < 7) return `${days}일 전`;
	const weeks = Math.floor(days / 7);
	if (weeks < 5) return `${weeks}주 전`;
	const months = Math.floor(days / 30);
	return `${months}개월 전`;
}

export const WORKOUT_LABELS: Record<string, string> = {
	rest: '휴식',
	recovery: '회복',
	easy: '쉬운 달리기',
	long: '장거리',
	long_run: '장거리',
	steady: '스테디',
	tempo: '템포',
	interval: '인터벌',
	repetition: '레피티션',
	sprint: '스프린트',
	race: '레이스'
};

export function workoutLabel(type: string): string {
	return WORKOUT_LABELS[type] ?? type;
}

export function formatRelativeDay(isoDate: string): string {
	const date = new Date(isoDate);
	const today = new Date();
	const diffDays = Math.round(
		(Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()) -
			Date.UTC(date.getFullYear(), date.getMonth(), date.getDate())) /
			86_400_000
	);
	if (diffDays === 0) return '오늘';
	if (diffDays === 1) return '어제';
	if (diffDays > 1) return `${diffDays}일 전`;
	return date.toLocaleDateString('ko-KR');
}
