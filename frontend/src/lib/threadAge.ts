// 마지막 메시지가 7일 넘게 지난 스레드는 "당시 기준"임을 알린다 — 지금 상태와 다를 수 있다.
export function staleLabel(lastMessageAt: string | null | undefined, nowMs: number): string | null {
	if (!lastMessageAt) return null;
	const t = Date.parse(lastMessageAt.includes('T') ? lastMessageAt : lastMessageAt.replace(' ', 'T') + 'Z');
	if (!Number.isFinite(t)) return null;
	const days = Math.floor((nowMs - t) / 86_400_000);
	return days >= 7 ? `${days}일 전 대화 · 당시 기준` : null;
}
