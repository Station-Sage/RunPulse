export interface ImpactLite {
	ctl_contribution: number | null;
	tsb: number | null;
	similar: {
		basis?: 'same_course' | 'same_class' | 'distance';
		n: number;
		pace_rank: number;
		avg_pace_sec_km: number;
		pace_diff_sec: number;
		class_label?: string;
		load_median?: number | null;
		load_pct_vs_median?: number | null;
	} | null;
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
		const group = s.basis === 'same_course' ? '같은 코스' : s.basis === 'same_class' ? `같은 ${s.class_label ?? '유형'}` : '비슷한 거리';
		out.push(`${group} 이전 ${s.n}회 중 ${s.pace_rank}번째로 빠른 페이스 (평균보다 ${cmp})`);
		if (s.load_median != null && s.load_pct_vs_median != null) {
			const p = Math.round(s.load_pct_vs_median);
			out.push(`부하 대비: ${group} 중앙값 ${Math.round(s.load_median)} 대비 ${p >= 0 ? '+' : ''}${p}%`);
		}
	} else {
		out.push('판정할 기준이 아직 부족해요(같은 유형·코스 기록 5회 필요)');
	}
	if (i.race) out.push(`${i.race.name} D-${i.race.days_left}에 쌓은 세션`);
	return out;
}
