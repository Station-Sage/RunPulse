// Coach 엔진 표기 순수 함수 (30-coach-chat design §4.1·§7.2) — 화면은 이 결과만 그린다.
import type { CoachEngine, EngineView, ScopeItem } from '$lib/types';

const REASON_TEXT: Record<string, string> = {
	http_404: '연결 실패(404)',
	http_401: '인증 실패(401)',
	http_429: '사용량 한도(429)',
	http_5xx: '서버 오류(5xx)',
	timeout: '시간 초과',
	no_key: '키 없음',
	parse_error: '응답 해석 실패',
	user_skip: '사용자 선택',
	no_consent: '동의 필요',
	network: '네트워크 오류'
};

export function reasonText(reason: string | null | undefined): string {
	return REASON_TEXT[reason ?? ''] ?? (reason || '알 수 없음');
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

export type MessageBanner = 'fallback' | 'rule_only' | 'error' | null;

/** 메시지 아래 배너 종류 — fallback은 "AI로 다시 생성", rule_only는 "AI 설정" 링크를 단다. */
export function bannerFor(engine: EngineView | undefined): MessageBanner {
	if (!engine) return null;
	if (engine.status === 'fallback') return 'fallback';
	if (engine.status === 'rule_only') return 'rule_only';
	if (engine.status === 'error') return 'error';
	return null;
}

/** 전송 범위 시트 — 메모 제외 토글이 켜지면 선택 항목을 뺀 목록. */
export function visibleScope(scope: ScopeItem[], excludeNotes: boolean): ScopeItem[] {
	return excludeNotes ? scope.filter((s) => !s.optional) : scope;
}
