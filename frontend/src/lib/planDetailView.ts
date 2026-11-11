// 플랜 상세·세션·비교 화면의 작은 표시 규칙(V2-AUDIT 묶음 E: P-10·P-14·P-16·P-20).

/** P-10: ACWR 적정 범위 문구 — 서버가 메트릭 정의에서 보낸 범위만 쓴다(없으면 null, 하드코딩 없음). */
export function acwrRangeText(range: [number, number] | null | undefined): string | null {
	if (!range || range.length !== 2 || !range.every(Number.isFinite)) return null;
	return `적정 ${range[0]}~${range[1]}`;
}

/** P-10: CTL 막대 — 최근 1년 최고 대비 비율. 기준이 없으면 막대 없이 숫자만(null). */
export function ctlBar(
	current: number | null | undefined,
	scale: { max: number; label: string } | null | undefined
): { pct: number; caption: string } | null {
	if (current == null || !scale || !(scale.max > 0)) return null;
	const pct = Math.max(0, Math.min(100, Math.round((current / scale.max) * 100)));
	return { pct, caption: `${scale.label} ${Math.round(scale.max)} 대비 ${pct}%` };
}

/** P-16: 메모 저장 버튼 — 바뀐 게 있을 때만. 비우고 저장하면 지우기(기존 메모가 있을 때). */
export function noteAction(text: string, saved: string): 'save' | 'clear' | null {
	const now = text.trim();
	const before = saved.trim();
	if (now === before) return null;
	return now ? 'save' : 'clear';
}

/** P-14: 새 플랜 흐름의 단계 표시 — 입력(1) → 비교·선택(2). */
export const PLAN_FLOW_STEPS = 2;
export function planStepText(step: 1 | 2): string {
	return `단계 ${step}/${PLAN_FLOW_STEPS}`;
}

/** P-20: 다시 맞추기 시작점 카드의 목표 기록 줄 — 목표가 없으면 '없음 바꾸기' 대신 정하기로 안내. */
export function targetLine(goalText: string | null): { text: string; action: string } {
	return goalText
		? { text: `목표 기록 ${goalText}`, action: '바꾸기' }
		: { text: '목표 기록 없이 완주를 목표로 하고 있어요', action: '목표 기록 정하기' };
}
