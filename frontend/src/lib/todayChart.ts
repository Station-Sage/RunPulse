// 오늘 화면 폼 차트 로딩 규칙(T-25·T-28) — 순수 함수. 테스트: tests/todayChart.test.mjs
import type { MetricTrendData, TodayResponse } from './types/index.ts';

/** 부하 지표(CTL)가 있을 때만 3개월 추세를 요청한다 — 없으면 빈 추세로 차트 블록을 숨긴다. */
export function shouldFetchChart(today: Pick<TodayResponse, 'status'>): boolean {
	return today.status?.training_status?.ctl != null;
}

/** '데이터 수집 중' 빈 추세(차트 블록은 점이 2개 미만이면 숨는다). */
export function emptyTrendData(slug: string): MetricTrendData {
	return { slug, label: slug, unit: '', current: null, peak: null, change_pct: null, points: [] };
}
