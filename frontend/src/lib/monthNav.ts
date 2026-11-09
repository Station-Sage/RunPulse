// 월간 내러티브 페이지(/today/month/[ym]) 순수 헬퍼 — T-21·T-23·T-24. 테스트: tests/monthNav.test.mjs

/** 이전 달 이동 하한 — `normalizeMonthParam` 이 받는 가장 이른 달과 같다(T-21). */
export const MIN_YEAR = 2000;

export function isAtMinMonth(year: number, month: number): boolean {
	return year < MIN_YEAR || (year === MIN_YEAR && month <= 1);
}

/**
 * 닫기(‹ 오늘) 동작(T-23) — 직전 화면이 앱 안의 오늘 화면일 때만 뒤로가기, 그 밖(딥링크·다른 화면)은 오늘로 이동.
 * @param fromPath 이 페이지로 들어오기 직전 경로(afterNavigate 의 from, 없으면 null)
 */
export function closeAction(fromPath: string | null, base: string): 'back' | 'today' {
	return fromPath === `${base}/today` || fromPath === `${base}/today/` ? 'back' : 'today';
}

type Pt = { date: string; value: number | null };

/**
 * 스파크라인 구간(T-24) — 이번 달이면 최근 28일, 과거 달이면 그 달 날짜만. 1년 추세 하나로 모든 달을 같은 모양으로 그린다.
 */
export function monthSlice(points: Pt[], year: number, month: number, isCurrent: boolean): Pt[] {
	if (isCurrent) return points.slice(-28);
	const ym = `${year}-${String(month).padStart(2, '0')}`;
	return points.filter((p) => p.date.startsWith(ym));
}
