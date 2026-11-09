// 체크인 행 → QuickInput existing 표현. coach·today 공용.
import type { CheckinPayload, CheckinRow, PainLevel, QuickInputExisting } from '$lib/types';

export function toQuickInputExisting(c: CheckinRow | null): QuickInputExisting | undefined {
	if (!c) return undefined;
	return { fatigue: c.fatigue ?? undefined, pain: c.pain ?? undefined, note: c.note ?? undefined, timestamp: c.created_at };
}

/** 메모 최대 길이 — 서버 `input_limits.CHECKIN_NOTE_MAX` 와 같은 값(T-17). */
export const CHECKIN_NOTE_MAX = 500;

/** 저장 버튼 페이로드 — 비운 통증·메모는 null 로 보내 지운다(서버는 실린 키만 갱신, T-16). 피로 미선택은 보내지 않는다. */
export function checkinSavePayload(fatigue: number | undefined, pain: PainLevel | undefined, note: string): CheckinPayload {
	const out: CheckinPayload = { pain: pain ?? null, note: note.trim() || null };
	if (fatigue !== undefined) out.fatigue = fatigue;
	return out;
}

/** 되돌리기 페이로드 — 저장 직전 기록으로 세 값을 모두 되돌린다(없던 값은 null, T-19). */
export function checkinUndoPayload(prev: CheckinRow | null): CheckinPayload {
	return { fatigue: prev?.fatigue ?? null, pain: prev?.pain ?? null, note: prev?.note ?? null };
}
