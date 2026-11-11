// 마지막 메시지가 7일 넘게 지난 스레드는 "당시 기준"임을 알린다 — 지금 상태와 다를 수 있다.
export function staleLabel(lastMessageAt: string | null | undefined, nowMs: number): string | null {
	if (!lastMessageAt) return null;
	const t = Date.parse(lastMessageAt.includes('T') ? lastMessageAt : lastMessageAt.replace(' ', 'T') + 'Z');
	if (!Number.isFinite(t)) return null;
	const days = Math.floor((nowMs - t) / 86_400_000);
	// C-15: 경과 시간은 행 오른쪽(마지막 대화 시각) 한 곳만 — 여기서는 '당시 기준'만 알린다
	return days >= 7 ? STALE_TEXT : null;
}

export const STALE_TEXT = '당시 기준 답변 · 지금 상태와 다를 수 있어요';

/** C-09: 경로의 스레드 id — 숫자로만 된 1 이상 정수만(12abc·-1·0 → null). */
export function parseThreadId(raw: string | null | undefined): number | null {
	if (!raw || !/^\d+$/.test(raw)) return null;
	const n = Number(raw);
	return Number.isSafeInteger(n) && n >= 1 ? n : null;
}

/** C-15: 행 오른쪽 시각 라벨 — 무엇의 시각인지 붙인다. */
export function lastTalkLabel(relative: string | null | undefined): string | null {
	return relative ? `마지막 대화 ${relative}` : null;
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
