// 코치 답변 한 건에서 실제로 시도한 provider(S4-87) — 서버 `coach_engine_health.attempt_views`. 옛 응답에는 없을 수 있다.
export interface EngineAttempt {
	provider: string;
	model: string | null;
	ok: boolean;
	reason: string | null;
}
