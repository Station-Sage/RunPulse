// AI 다듬기 표시(ADR-059) — 규칙 판정을 AI 가 문장으로 다듬은 경우(source==='ai')에만 'AI 해설' 표시를 붙인다.
// 규칙 문구(source==='rule')는 기본값이라 따로 표시하지 않는다('규칙 기반 요약' 라벨 폐지).
export type WordingSource = 'ai' | 'rule';

export const AI_MARK_LABEL = 'AI 해설';
export const AI_MARK_TITLE = '규칙이 내린 판정을 AI가 문장으로 다듬었어요. 수치는 원래 근거만 써요.';

export function isAiWorded(x: { source?: string | null } | string | null | undefined): boolean {
	return (typeof x === 'string' ? x : x?.source) === 'ai';
}

export function aiMarkText(prefix = false): string {
	return prefix ? `· ${AI_MARK_LABEL}` : AI_MARK_LABEL;
}
