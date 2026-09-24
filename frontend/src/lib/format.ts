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

export function formatDate(isoStr: string): string {
	return isoStr.slice(0, 10);
}

export function formatRelativeTime(isoStr: string): string {
	const diff = Date.now() - new Date(isoStr).getTime();
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
	tempo: '템포',
	interval: '인터벌',
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
