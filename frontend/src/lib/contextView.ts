// 컨텍스트 칩·목록의 순수 표시 로직 (NEW-7·19·22, 문구는 의미 먼저·진단 표현 없음).
export type ContextKind = 'illness' | 'travel' | 'altitude';
export type ConsentAction = 'grant' | 'decline' | 'revoke';

export interface ContextEpisode {
	id: number;
	kind: ContextKind;
	start_date: string;
	end_date: string | null;
	severity: number | null;
	detail: { site?: string; delta_h?: number; direction?: 'east' | 'west'; altitude_m?: number; band?: string };
	origin: 'manual' | 'auto';
	status: 'candidate' | 'confirmed' | 'dismissed';
	last_confirmed_date: string | null;
}

export interface ConsentState { action: string | null; needs_first_prompt: boolean }
export interface ContextList {
	episodes: ContextEpisode[];
	illness_reconfirm: { episode_id: number; days_since: number } | null;
	consent: ConsentState;
	health_question: boolean;
}

export const KIND_LABEL: Record<ContextKind, string> = { illness: '아파요', travel: '이동·시차', altitude: '고지대' };
export const SEVERITY: { value: number; label: string }[] = [
	{ value: 1, label: '가벼워요' },
	{ value: 2, label: '많이 아파요' }
];
export const ALT_BANDS: { key: string; label: string; m: number }[] = [
	{ key: 'low', label: '1500m 미만', m: 1000 },
	{ key: 'mid', label: '1500–2500m', m: 2000 },
	{ key: 'high', label: '2500m 이상', m: 2600 }
];
export const SITES = ['목', '코', '가슴', '배', '전신'];

export function isOpen(e: ContextEpisode): boolean {
	return e.end_date === null && e.status !== 'dismissed';
}

export function episodeLabel(e: ContextEpisode): string {
	if (e.kind === 'illness') {
		const sev = SEVERITY.find((s) => s.value === e.severity)?.label;
		return ['아팠던 기록', sev, e.detail.site].filter(Boolean).join(' · ');
	}
	if (e.kind === 'travel') {
		const h = e.detail.delta_h;
		const dir = e.detail.direction === 'east' ? '동쪽' : e.detail.direction === 'west' ? '서쪽' : '';
		return h != null ? `이동·시차 ${dir} +${h}시간` : '이동·시차';
	}
	const m = e.detail.altitude_m;
	return m != null ? `고지대 약 ${m}m` : '고지대';
}

/** 체크인 최상단 확인 질문(Level 0). 우선순위: 이어지는 질병 → 7일 재확인 → 자동 후보 → 몸 상태 질문. */
export interface ConfirmPrompt { key: string; text: string; episodeId?: number; primary: string; secondary: string }
export function confirmPrompts(list: ContextList | null): ConfirmPrompt[] {
	if (!list) return [];
	const out: ConfirmPrompt[] = [];
	const re = list.illness_reconfirm;
	if (re) out.push({ key: `re-${re.episode_id}`, text: `아팠던 지 ${re.days_since}일째예요 — 아직 아픈가요?`, episodeId: re.episode_id, primary: '계속 아파요', secondary: '나았어요' });
	for (const e of list.episodes) {
		if (e.status === 'candidate' && e.origin === 'auto') {
			out.push({ key: `c-${e.id}`, text: `${episodeLabel(e)} 감지 — 맞아요?`, episodeId: e.id, primary: '맞아요', secondary: '아니에요' });
		}
	}
	if (list.health_question && !list.episodes.some((e) => e.kind === 'illness' && isOpen(e))) {
		out.push({ key: 'health', text: '몸 상태 어때요?', primary: '아파요', secondary: '괜찮아요' });
	}
	return out;
}

export function staleBanner(list: ContextList | null): string | null {
	const re = list?.illness_reconfirm;
	return re ? `아팠던 지 ${re.days_since}일째예요. 지금은 어때요?` : null;
}

/** `/today` 응답의 context 블록(src/api/routes_today.py). */
export interface TodayContext {
	active: ContextEpisode[];
	illness_reconfirm: ContextList['illness_reconfirm'];
	health_question: boolean;
}
