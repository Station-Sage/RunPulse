// AI 설정 화면 표시 헬퍼.
import type { AiSettings, KeyState } from '$lib/api/data';

const NAMES: Record<string, string> = { gemini: 'Gemini', groq: 'Groq', openai: 'OpenAI', claude: 'Claude', claude_queue: 'Claude(구독)', rule: '규칙 기반' };

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

/** 오늘 AI 사용량 한 줄 — 한도·자정 초기화 안내(multiuser-sync §4.3). 없으면 빈 문자열. */
export function usageTodayText(u: AiSettings['usage_today']): string {
	if (!u) return '';
	const head = `오늘 AI 호출 ${u.calls}/${u.limit_calls}회 · 토큰 ${u.tokens.toLocaleString('ko-KR')}/${u.limit_tokens.toLocaleString('ko-KR')}`;
	return u.calls >= u.limit_calls || u.tokens >= u.limit_tokens ? `${head} · 한도 도달(자정 초기화)` : head;
}

export function usageText(u: AiSettings['usage_7d']): string {
	if (!u.messages) return '최근 7일 답변이 없어요';
	const parts = Object.entries(u.by_provider).map(([p, n]) => `${providerName(p)} ${n}회`);
	if (u.fallback) parts.push(`규칙 대체 ${u.fallback}회`);
	if (u.rule) parts.push(`규칙 답변 ${u.rule}회`);
	return `최근 7일 답변 ${u.messages}건 · ${parts.join(' · ')}${u.tool_calls ? ` · 데이터 조회 ${u.tool_calls}회` : ''}`;
}

/** D-23: API 키 형식 점검(서버 key_format_error 와 같은 규칙) — 문제 있으면 안내 문구, 없으면 null. 앞뒤 공백은 서버가 지운다. */
export function keyFormatError(raw: string): string | null {
	const k = raw.trim();
	if (!k) return null;
	if (k.length > 256) return 'API 키는 256자 이하예요';
	if (!/^[\x21-\x7e]+$/.test(k) || /[<>"'`]/.test(k)) return 'API 키에 공백·줄바꿈이나 쓸 수 없는 문자가 있어요. 복사한 키를 다시 확인해 주세요';
	return null;
}

/** Claude 큐 라디오의 선택 가능 여부와 안내 문구 — 켜져 있지 않으면 선택할 수 없다. */
export function queueOption(q: { enabled: boolean; worker_up: boolean } | null): { disabled: boolean; note: string } {
	if (!q) return { disabled: true, note: '상태를 확인하지 못했어요' };
	if (!q.enabled) return { disabled: true, note: '이 계정은 Claude 큐가 꺼져 있어요(서버 설정에서 켜야 해요)' };
	return { disabled: false, note: q.worker_up ? '워커 연결됨 · 실패하면 Groq/Gemini → 규칙 순으로 대신해요' : '워커가 응답하지 않아요 · 지금은 다른 제공자로 대신해요' };
}
