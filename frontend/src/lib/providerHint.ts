export interface ProviderStatusLite {
	has_data: boolean;
	last_synced_at: string | null;
	activity_count: number;
}

// 상태 표만으로는 조치가 안 보이므로 다음 행동을 한 줄로 말한다. 정상이면 null.
export function providerHint(item: ProviderStatusLite, nowMs: number): string | null {
	if (!item.has_data) return '데이터 없음 — 연동 전이거나 동기화가 실패했어요. 동기화를 실행해 보세요.';
	if (!item.last_synced_at) return null;
	const t = Date.parse(item.last_synced_at.includes('T') ? item.last_synced_at : item.last_synced_at.replace(' ', 'T') + 'Z');
	if (!Number.isFinite(t)) return null;
	const days = Math.floor((nowMs - t) / 86_400_000);
	if (days >= 30) return `${days}일째 동기화가 없어요 — 최근 활동이 빠져 있을 수 있어요.`;
	if (days >= 7) return `${days}일 전이 마지막 동기화예요.`;
	return null;
}

// 목록의 모든 활동이 같은 소스면 행마다 배지를 반복하지 않는다(정보량 0).
export function showSourceBadge(sources: string[]): boolean {
	return new Set(sources).size > 1;
}
