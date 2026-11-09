// 활동 상세 화면 순수 로직 — 환경 줄 항목, 빈 상태 원인·다음 행동, 피드백 요약(UX 리뷰 A-05·A-06·A-27·S-16).
import { providerLabelCompact } from './provider.ts';
import type { ActivityDetail, ActivityEnvironment, ActivityFeedback, ProviderKey } from './types/index.ts';

export interface EnvItem {
	label: string;
	value: string;
}

/** 환경 줄에 실제로 보일 항목. 비면 카드 자체를 숨긴다(A-06). 페이스 영향은 반올림해 0이면 생략. */
export function envItems(env: ActivityEnvironment | null | undefined): EnvItem[] {
	if (!env) return [];
	const out: EnvItem[] = [];
	if (env.temp_c != null) out.push({ label: '기온', value: `${Math.round(env.temp_c)}°C` });
	if (env.dew_point_c != null) out.push({ label: '이슬점', value: `${Math.round(env.dew_point_c)}°C` });
	const eff = env.pace_effect_sec_km != null ? Math.round(env.pace_effect_sec_km) : 0;
	if (eff !== 0) out.push({ label: '페이스 영향', value: `${eff > 0 ? '+' : ''}${eff}초/km` });
	return out;
}

export interface EmptyNote {
	/** 원인 한 줄 */
	reason: string;
	/** 다음 행동 링크(base 제외 경로). 없으면 안내만. */
	action: { label: string; path: string } | null;
}

const NO_RECORD_FAMILIES: Record<string, string> = { strength: '근력 운동', other: '이 종목' };

/** 소스 이름 목록 — 형제(병합) 소스가 있으면 모두, 없으면 대표 소스. */
function sourceNames(a: Pick<ActivityDetail, 'core' | 'siblings'>): string {
	const list = a.siblings && a.siblings.length > 0 ? a.siblings.map((s) => s.provider) : [a.core.source];
	return [...new Set(list.map((p) => providerLabelCompact(p as ProviderKey)))].join('·');
}

/** 스트림/랩이 비었을 때 원인과 다음 행동(A-05·S-16). 근력 등은 원래 기록이 없다고만 알린다. */
export function emptyDataNote(
	kind: 'streams' | 'laps',
	a: Pick<ActivityDetail, 'core' | 'siblings' | 'display'> | null | undefined
): EmptyNote {
	const what = kind === 'streams' ? '초 단위 기록(심박·페이스 흐름)' : '랩 기록';
	if (!a) return { reason: `${what}이 없어요.`, action: null };
	const fam = a.display?.family ?? '';
	if (NO_RECORD_FAMILIES[fam]) {
		return { reason: `${NO_RECORD_FAMILIES[fam]}은 ${kind === 'streams' ? '초 단위 기록' : '랩'}을 남기지 않는 경우가 많아요.`, action: null };
	}
	return {
		reason: `${sourceNames(a)}에서 이 활동의 ${what}을 받지 못했어요.`,
		action: { label: '동기화 상태 보기', path: '/data/sync' }
	};
}

/** 탭 바에 '없음'을 미리 표시할 탭(S-16). 상세 응답이 없으면(오류·404) 표시하지 않는다. */
export function emptyTabs(a: Pick<ActivityDetail, 'stream_point_count' | 'laps'> | null | undefined): ('streams' | 'laps')[] {
	if (!a) return [];
	const out: ('streams' | 'laps')[] = [];
	if (!a.stream_point_count) out.push('streams');
	if (!a.laps || a.laps.length === 0) out.push('laps');
	return out;
}

const PAIN_LABEL: Record<string, string> = { mild: '경미', moderate: '중간', severe: '심함' };

/** 요약 버튼 문자열 — `RPE 6 · 통증 경미 · 메모…`. 메모는 40자에서 자른다(A-27). */
export function feedbackSummary(fb: ActivityFeedback | null | undefined, noteMax = 40): string {
	if (!fb) return '';
	const parts: string[] = [];
	if (fb.rpe) parts.push(`RPE ${fb.rpe}`);
	if (fb.pain && fb.pain !== 'none') parts.push(`통증 ${PAIN_LABEL[fb.pain] ?? fb.pain}`);
	const note = fb.note?.trim();
	if (note) parts.push(note.length > noteMax ? `${note.slice(0, noteMax)}…` : note);
	return parts.join(' · ');
}

/** 저장할 내용이 있는지 — 새 피드백인데 전부 비었으면 저장 버튼을 막는다(A-25, 서버는 `{}`를 200+null 로 받음). */
export function feedbackHasInput(v: { rpe: number | null; pain: string | null; note: string }): boolean {
	return v.rpe != null || v.pain != null || v.note.trim() !== '';
}

/** 활동을 못 연 경우의 한 화면 문구 — 잘못된 주소와 없는 활동을 구분(A-24·E-28). 404 가 아니면 null(오류 화면이 따로 처리). */
export function missingActivityView(failure: { kind: string; code: string } | null | undefined): { title: string; body: string } | null {
	if (!failure || failure.kind !== 'not_found') return null;
	if (failure.code === 'BAD_ID') return { title: '주소가 올바르지 않아요', body: '활동 주소의 번호를 확인해 주세요.' };
	return { title: '활동을 찾을 수 없어요', body: '삭제됐거나 주소가 바뀌었을 수 있어요.' };
}

/** 경로 id 가 잘못됐을 때 load 가 돌려주는 실패(모든 탭 공용). */
export const BAD_ID_FAILURE = { kind: 'not_found', status: 404, code: 'BAD_ID', detail: 'bad id' } as const;
