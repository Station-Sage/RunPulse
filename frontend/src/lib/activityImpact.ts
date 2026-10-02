export interface ImpactLite {
	ctl_contribution: number | null;
	tsb: number | null;
	similar: { n: number; pace_rank: number; avg_pace_sec_km: number; pace_diff_sec: number } | null;
	race: { name: string; days_left: number } | null;
}

// 화면에 줄 문장 목록 — 값이 없는 항목은 만들지 않는다(근거 없는 문장 금지).
export function impactLines(i: ImpactLite): string[] {
	const out: string[] = [];
	if (i.ctl_contribution != null) out.push(`이 날 체력(CTL) ${i.ctl_contribution >= 0 ? '+' : ''}${i.ctl_contribution.toFixed(1)}${i.tsb != null ? ` · 폼(TSB) ${i.tsb >= 0 ? '+' : ''}${Math.round(i.tsb)}` : ''}`);
	if (i.similar) {
		const s = i.similar;
		const d = Math.abs(Math.round(s.pace_diff_sec));
		const cmp = s.pace_diff_sec < 0 ? `${d}초/km 빠름` : s.pace_diff_sec > 0 ? `${d}초/km 느림` : '평균과 같음';
		out.push(`비슷한 거리 이전 ${s.n}회 중 ${s.pace_rank}번째로 빠른 페이스 (평균보다 ${cmp})`);
	}
	if (i.race) out.push(`${i.race.name} D-${i.race.days_left}에 쌓은 세션`);
	return out;
}
