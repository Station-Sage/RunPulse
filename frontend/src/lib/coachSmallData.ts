// Coach S2(소량 데이터) 안내 — DESIGN-P7-REVIEW03 L4. 데이터가 모이는 동안 할 일과 근거 한계 문구.
import { isSmallData, type UnlockMap } from './unlock.ts';

export interface SmallDataTodo {
	id: 'goal' | 'recent' | 'baseline';
	label: string;
	/** 'chat'이면 Coach 자유 질문으로 시작, 'link'이면 경로 이동(base 제외). */
	kind: 'chat' | 'link';
	target: string;
}

export const SMALL_DATA_TODOS: SmallDataTodo[] = [
	{ id: 'goal', label: '목표 대회 정하기', kind: 'link', target: '/coach/plan/new' },
	{ id: 'recent', label: '최근 기록 해석', kind: 'chat', target: '최근 기록 해석해줘' },
	{ id: 'baseline', label: '기준값 확인', kind: 'link', target: '/data/settings/profile' }
];

export function smallDataTodos(u: UnlockMap | null | undefined): SmallDataTodo[] {
	return isSmallData(u) ? SMALL_DATA_TODOS : [];
}

/** 근거가 얇을 때 코치가 먼저 밝히는 한계 문구. 충분하면 null. */
export function evidenceLimitNotice(u: UnlockMap | null | undefined): string | null {
	if (!u || u.ctl.unlocked) return null;
	const days = u.ctl.have_days;
	if (days <= 0) return '아직 훈련 기록이 없어 추세는 말하기 일러요 (CTL 미산출)';
	return `아직 ${days}일치라 추세는 말하기 일러요 (CTL 미산출)`;
}
