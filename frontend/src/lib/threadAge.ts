// 마지막 메시지가 7일 넘게 지난 스레드는 "당시 기준"임을 알린다 — 지금 상태와 다를 수 있다.
export function staleLabel(lastMessageAt: string | null | undefined, nowMs: number): string | null {
	if (!lastMessageAt) return null;
	const t = Date.parse(lastMessageAt.includes('T') ? lastMessageAt : lastMessageAt.replace(' ', 'T') + 'Z');
	if (!Number.isFinite(t)) return null;
	const days = Math.floor((nowMs - t) / 86_400_000);
	return days >= 7 ? `${days}일 전 대화 · 당시 기준` : null;
}

/** 제목이 같은 스레드에는 시작 날짜(M/D)를 붙여 구분한다 — 같은 주제 칩을 여러 번 눌러도 목록에서 구별된다. */
export function threadTitles(threads: { id: number; title: string; created_at: string }[]): Map<number, string> {
	const count = new Map<string, number>();
	for (const t of threads) count.set(t.title, (count.get(t.title) ?? 0) + 1);
	const out = new Map<number, string>();
	for (const t of threads) {
		if ((count.get(t.title) ?? 0) < 2) {
			out.set(t.id, t.title);
			continue;
		}
		const ms = Date.parse(t.created_at.includes('T') ? t.created_at : t.created_at.replace(' ', 'T') + 'Z');
		const d = Number.isFinite(ms) ? new Date(ms) : null;
		out.set(t.id, d ? `${t.title} · ${d.getMonth() + 1}/${d.getDate()}` : t.title);
	}
	return out;
}
