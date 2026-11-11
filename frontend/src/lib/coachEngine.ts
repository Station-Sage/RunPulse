// Coach 엔진 표기 순수 함수 (30-coach-chat design §4.1·§7.2) — 화면은 이 결과만 그린다.
import type { CoachEngine, EngineView, ScopeItem } from '$lib/types';
import type { EngineAttempt } from '$lib/types/engineAttempt';

const REASON_TEXT: Record<string, string> = {
	http_404: '연결 실패(404)',
	http_401: '인증 실패(401)',
	http_429: '사용량 한도(429)',
	http_5xx: '서버 오류(5xx)',
	http_4xx: '요청 거부(4xx)',
	timeout: '시간 초과',
	no_key: '키 없음',
	parse_error: '응답 해석 실패',
	user_skip: '사용자 선택',
	no_consent: '동의 필요',
	network: '네트워크 오류',
	unexpected: '예기치 못한 오류',
	quota_user: '오늘 AI 사용 한도',
	quota_global: 'AI 사용량 일시 제한',
	busy: 'AI 요청 혼잡'
};

export function reasonText(reason: string | null | undefined): string {
	return REASON_TEXT[reason ?? ''] ?? (reason || '알 수 없음');
}

/** fallback 배너 문구 — 사용량 한도는 "실패"가 아니라 한도 도달로 안내한다(multiuser-sync §4.3). */
export function fallbackText(reason: string | null | undefined): string {
	if (reason === 'quota_user') return '오늘 AI 사용 한도에 도달해 규칙 답변으로 대신했어요(자정 초기화)';
	if (reason === 'quota_global') return 'AI 사용량이 일시적으로 제한돼 규칙 답변으로 대신했어요';
	if (reason === 'busy') return 'AI 요청이 몰려 규칙 답변으로 대신했어요 · 잠시 뒤 다시 생성해 보세요';
	return `AI 연결에 실패해 규칙 답변으로 대신했어요 · ${reasonText(reason)}`;
}

/** LLM을 쓸 수 있는데 이 provider로는 아직 동의하지 않았다면 첫 전송 전에 동의 시트를 띄운다. */
export function needsConsent(engine: CoachEngine | null): boolean {
	if (!engine || engine.mode !== 'llm') return false;
	return !engine.consent || engine.consent.provider !== engine.selected.provider;
}

/** 입력창 위 한 줄 — "답변 엔진: …". */
export function engineLineText(engine: CoachEngine | null): string {
	if (!engine) return '';
	if (engine.mode === 'rule_by_choice') return '답변 엔진: 규칙 (AI 끔)';
	if (engine.mode === 'rule_only') return '답변 엔진: 규칙 (AI 미설정)';
	const head = engine.chain[0] ?? engine.selected;
	const name = head.model ? `${head.provider} · ${head.model}` : head.provider;
	if (needsConsent(engine)) return `답변 엔진: ${name} (첫 전송 전 동의 필요)`;
	return `답변 엔진: ${name}`;
}

export type MessageBanner = 'fallback' | 'rule_only' | 'error' | 'cancelled' | null;

/** 메시지 아래 배너 종류 — fallback은 "AI로 다시 생성", rule_only는 "AI 설정" 링크를 단다. */
export function bannerFor(engine: EngineView | undefined): MessageBanner {
	if (!engine) return null;
	if (engine.status === 'fallback') return 'fallback';
	if (engine.status === 'rule_only') return 'rule_only';
	if (engine.status === 'error') return 'error';
	if (engine.status === 'cancelled') return 'cancelled';
	return null;
}

/** 전송 범위 시트 — 메모 제외 토글이 켜지면 선택 항목을 뺀 목록. */
export function visibleScope(scope: ScopeItem[], excludeNotes: boolean): ScopeItem[] {
	return excludeNotes ? scope.filter((s) => !s.optional) : scope;
}

// ── C-17(ADR-055): 동의창 — 재시도 제공자를 이름으로 밝히고, 재시도는 opt-in·메모는 기본 제외 ──
const PROVIDER_NAMES: Record<string, string> = { gemini: 'Gemini', groq: 'Groq', openai: 'OpenAI', claude: 'Claude' };

export function providerName(p: string | null | undefined): string {
	return PROVIDER_NAMES[p ?? ''] ?? (p || '');
}

/** 동의 전 기본값 — 저장된 동의가 있으면 그 값을 그대로 쓴다(기존 사용자 유지). */
export function consentDefaults(c: { exclude_notes: boolean; tools_enabled: boolean; fallback_enabled: boolean } | null | undefined) {
	return {
		excludeNotes: c?.exclude_notes ?? true,
		toolsEnabled: c?.tools_enabled ?? true,
		fallbackEnabled: c?.fallback_enabled ?? false
	};
}

/** 재시도 대상 이름 목록("Groq"). 없으면 빈 문자열 — 토글을 숨긴다. */
export function fallbackNames(engine: Pick<CoachEngine, 'fallback_providers'>): string {
	return (engine.fallback_providers ?? []).map((f) => f.label || providerName(f.provider)).join('·');
}

/** 동의 문구(TXT-1 잠정) — 기본 제공자와, 재시도를 켜면 함께 전송될 제공자를 같이 밝힌다. */
export function consentText(engine: Pick<CoachEngine, 'selected' | 'fallback_providers'>): string {
	const main = providerName(engine.selected.provider);
	const fb = fallbackNames(engine);
	const tail = fb ? ` '실패 시 다른 AI로 재시도'를 켜면 ${main} 응답이 실패했을 때 같은 내용이 ${fb} 서버로도 전송돼요(기본은 꺼짐).` : '';
	return `질문과 아래 러닝 데이터가 ${main} 서버로 전송돼요.${tail} 동의해야 AI 답변을 쓸 수 있고, 동의 전에는 아무것도 전송하지 않아요.`;
}

/**
 * '원인 보기' 시도 줄(S4-87) — 이 답변에서 실제로 시도한 provider 를 순서대로, 실패면 사유를 붙인다.
 * 서버가 attempts 를 주지 않는 옛 응답만 지금 설정된 provider(fallbackGuess) 한 줄로 대신한다.
 */
export function attemptLines(
	attempts: EngineAttempt[] | null | undefined,
	fallbackGuess: { provider: string; model?: string | null } | null
): string[] {
	const name = (p: string, m?: string | null) => (m ? `${providerName(p)} · ${m}` : providerName(p));
	if (attempts && attempts.length) return attempts.map((a) => `${name(a.provider, a.model)} — ${a.ok ? '성공' : reasonText(a.reason)}`);
	return fallbackGuess ? [name(fallbackGuess.provider, fallbackGuess.model)] : [];
}

/** 성공했지만 앞서 실패한 시도가 있는 답변(S4-88) — 메시지에 '시도 기록 ›'을 달아 원인 보기 시트를 연다. */
export function hasFailedRetry(engine: Pick<EngineView, 'status' | 'attempts'> | undefined): boolean {
	return engine?.status === 'ok' && (engine.attempts ?? []).some((a) => !a.ok);
}
