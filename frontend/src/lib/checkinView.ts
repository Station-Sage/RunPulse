// 체크인 행 → QuickInput existing 표현. coach·today 공용.
import type { CheckinRow, QuickInputExisting } from '$lib/types';

export function toQuickInputExisting(c: CheckinRow | null): QuickInputExisting | undefined {
	if (!c) return undefined;
	return { fatigue: c.fatigue ?? undefined, pain: c.pain ?? undefined, note: c.note ?? undefined, timestamp: c.created_at };
}
