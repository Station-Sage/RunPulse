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
