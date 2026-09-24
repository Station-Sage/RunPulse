// 기준 시점 라벨 — status.date가 서버 로컬 오늘이면 "오늘 지금까지 반영", 아니면 그 날짜 기준.
export function asOfLabel(statusDate: string, todayLocal: string): string {
	const [, m, d] = statusDate.split('-');
	const md = `${Number(m)}월 ${Number(d)}일`;
	return statusDate === todayLocal ? `${md} · 오늘 지금까지 반영` : `${md} 기준`;
}

// 브라우저 로컬 날짜 YYYY-MM-DD
export function localDateString(now: Date = new Date()): string {
	const p = (n: number) => String(n).padStart(2, '0');
	return `${now.getFullYear()}-${p(now.getMonth() + 1)}-${p(now.getDate())}`;
}
