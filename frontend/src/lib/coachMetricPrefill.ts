// 지표 분해 → Coach 프리필(`/coach/new?metric=&date=`) — 쿼리 파싱·링크·추천 질문(순수 함수).

const SLUG = /^[a-z0-9_]+$/;
const DATE = /^\d{4}-\d{2}-\d{2}$/;

export interface MetricPrefill {
	slug: string;
	date: string;
}

export function parseMetricPrefill(params: URLSearchParams): MetricPrefill | null {
	const slug = params.get('metric');
	const date = params.get('date');
	return slug && date && SLUG.test(slug) && DATE.test(date) ? { slug, date } : null;
}

export function metricCoachHref(base: string, slug: string, date: string): string {
	return `${base}/coach/new?metric=${encodeURIComponent(slug)}&date=${date}`;
}

export function metricContextRef(p: MetricPrefill): string {
	return `${p.slug}@${p.date}`;
}

export function metricQuestions(name: string, valueText: string, date: string): string[] {
	const md = `${Number(date.slice(5, 7))}월 ${Number(date.slice(8, 10))}일`;
	return [
		`${md} ${name} ${valueText}은(는) 어떤 상태인가요?`,
		`${name}이(가) 이렇게 나온 가장 큰 원인이 뭐예요?`,
		`${name}을(를) 좋게 하려면 앞으로 무엇을 바꿔야 해요?`
	];
}
