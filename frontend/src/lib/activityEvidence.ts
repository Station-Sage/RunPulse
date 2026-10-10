// 활동 대화 근거 카드 — 칩 문구 구성과 스레드 복귀 경로(순수 함수).

export interface EvidenceInput {
	distance_km: number | null;
	pace: string | null;
	decoupling_pct: number | null;
	tsb: number | null;
}

/** 값이 있는 항목만 칩으로 만든다(없는 근거는 숨김). */
export function evidenceChips(a: EvidenceInput): string[] {
	const chips: string[] = [];
	if (a.distance_km != null) chips.push(`${a.distance_km.toFixed(1)}km`);
	if (a.pace) chips.push(`페이스 ${a.pace}`);
	if (a.decoupling_pct != null) chips.push(`디커플링 ${a.decoupling_pct.toFixed(1)}%`);
	if (a.tsb != null) chips.push(`TSB ${a.tsb > 0 ? '+' : ''}${a.tsb.toFixed(1)}`);
	return chips;
}

/** 활동 컨텍스트 스레드의 뒤로가기 목적지. 그 외는 Coach 홈. */
export function threadBackHref(
	context: { kind: string; ref: string } | null | undefined,
	base: string
): { href: string; label: string } {
	if (context?.kind === 'activity' && /^\d+$/.test(context.ref)) {
		return { href: `${base}/library/${context.ref}?from=coach`, label: '← 활동' };
	}
	const m = context?.kind === 'metric' ? /^([a-z0-9_]+)@(\d{4}-\d{2}-\d{2})$/.exec(context.ref) : null;
	if (m) return { href: `${base}/library/metrics/${m[1]}?date=${m[2]}`, label: '← 지표' };
	return { href: `${base}/coach`, label: '← Coach' };
}
