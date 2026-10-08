// AI 설정 화면 표시 헬퍼.
import type { AiSettings, KeyState } from '$lib/api/data';

const NAMES: Record<string, string> = { gemini: 'Gemini', groq: 'Groq', openai: 'OpenAI', claude: 'Claude', rule: '규칙 기반' };

export const providerName = (p: string): string => NAMES[p] ?? p;

export function keyStateText(s: KeyState): string {
	return s === 'set' ? '키 저장됨' : s === 'invalid' ? '키가 거부됐어요' : '키 없음';
}

/** 지금 Coach가 어떻게 답하는지 한 줄. */
export function engineSummary(s: AiSettings): string {
	if (s.mode === 'rule_by_choice') return '규칙 기반 · AI를 끔';
	if (s.mode === 'rule_only') return '규칙 기반 · API 키가 없어요';
	const name = providerName(s.provider);
	if (s.health.degraded) return `규칙 기반 · ${name} 오류로 대체${s.last_error_label ? ` (${s.last_error_label})` : ''}`;
	return s.chain.length > 1 ? `${name} · 실패 시 ${s.chain.slice(1).map((c) => providerName(c.provider)).join('→')}` : `${name} · 폴백 없음`;
}

export function usageText(u: AiSettings['usage_7d']): string {
	if (!u.messages) return '최근 7일 답변이 없어요';
	const parts = Object.entries(u.by_provider).map(([p, n]) => `${providerName(p)} ${n}회`);
	if (u.fallback) parts.push(`규칙 대체 ${u.fallback}회`);
	if (u.rule) parts.push(`규칙 답변 ${u.rule}회`);
	return `최근 7일 답변 ${u.messages}건 · ${parts.join(' · ')}${u.tool_calls ? ` · 데이터 조회 ${u.tool_calls}회` : ''}`;
}
