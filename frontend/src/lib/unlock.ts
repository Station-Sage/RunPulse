// 지표 해금 진행도 표시 규칙 — DESIGN-P7-REVIEW03 §2.5 (D-L7: 핵심 게이지 3종 중 하나라도 잠겼으면 '적은 데이터').
export type UnlockKey = 'ctl' | 'tsb' | 'cirs' | 'utrs';

export interface UnlockEntry {
	required_days: number;
	have_days: number;
	unlocked: boolean;
	basis: 'load_span' | 'wellness_days';
}

export type UnlockMap = Record<UnlockKey, UnlockEntry>;

export const CORE_GAUGES: UnlockKey[] = ['utrs', 'cirs', 'tsb'];

const LABEL: Record<UnlockKey, string> = { ctl: '체력(CTL)', tsb: '폼(TSB)', cirs: '부상 위험(CIRS)', utrs: '준비도(UTRS)' };

export function isSmallData(u: UnlockMap | null | undefined): boolean {
	if (!u) return false;
	return CORE_GAUGES.some((k) => !u[k].unlocked);
}

export interface UnlockRow {
	key: UnlockKey;
	label: string;
	pct: number;
	hint: string;
}

export function lockedRows(u: UnlockMap | null | undefined): UnlockRow[] {
	if (!u) return [];
	return CORE_GAUGES.filter((k) => !u[k].unlocked).map((k) => {
		const e = u[k];
		const left = Math.max(0, e.required_days - e.have_days);
		const what = e.basis === 'load_span' ? '훈련 기록' : '웰니스 기록';
		return {
			key: k,
			label: LABEL[k],
			pct: Math.min(100, Math.round((e.have_days / e.required_days) * 100)),
			hint: e.have_days === 0 ? `${what}이 들어오면 시작돼요` : `${what} ${left}일 더 쌓이면 열려요`
		};
	});
}
