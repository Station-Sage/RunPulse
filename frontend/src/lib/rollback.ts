// v1 복귀 로직(순수) — 기록 전송과 기본 화면 전환을 주입받아 테스트 가능하게 둔다.
export type RollbackReason = 'missing_feature' | 'hard_to_use' | 'slow_or_error' | 'just_looking';

export const ROLLBACK_REASONS: { value: RollbackReason; label: string }[] = [
	{ value: 'missing_feature', label: '필요한 기능이 없어요' },
	{ value: 'hard_to_use', label: '쓰기 어려워요' },
	{ value: 'slow_or_error', label: '느리거나 오류가 나요' },
	{ value: 'just_looking', label: '그냥 둘러봤어요' }
];

export const NOTE_MAX = 200;

export interface RollbackDeps {
	sendEvent: (body: Record<string, unknown>) => Promise<unknown>;
	setV1: () => Promise<unknown>;
	navigate: (url: string) => void;
	timeoutMs?: number;
}

/** 기록과 전환을 병렬로 최대 timeoutMs 기다린 뒤, 성공·실패와 무관하게 항상 v1로 이동한다. */
export async function rollbackToV1(reason: RollbackReason | null, note: string, d: RollbackDeps): Promise<void> {
	const trimmed = note.trim().slice(0, NOTE_MAX);
	const body: Record<string, unknown> = { kind: 'v1_rollback', reason };
	if (trimmed) body.reason_note = trimmed;
	let timer: ReturnType<typeof setTimeout> | undefined;
	const timeout = new Promise((r) => (timer = setTimeout(r, d.timeoutMs ?? 1500)));
	try {
		await Promise.race([Promise.allSettled([d.sendEvent(body), d.setV1()]), timeout]);
	} finally {
		clearTimeout(timer);
		d.navigate('/dashboard');
	}
}
