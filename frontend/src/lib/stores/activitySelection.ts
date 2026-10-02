// 활동 상세 선택 상태 — 스플릿·지도·타임라인이 공유(양방향 연동). 페이지 로컬 용도.
import { writable } from 'svelte/store';

export interface ActivitySelection {
	seg: number | null; // 스플릿 idx(1-based)
	cursorDist: number | null; // 타임라인 커서(m)
}

export const emptySelection: ActivitySelection = { seg: null, cursorDist: null };

export function createActivitySelection() {
	return writable<ActivitySelection>({ ...emptySelection });
}
