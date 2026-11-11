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

// C-07: 조사(은/는·이/가)를 지표 이름·값 뒤에 붙이지 않는 문장으로 — "체력 52은(는)" 같은 미해결 표기 제거
export function metricQuestions(name: string, valueText: string, date: string): string[] {
	const md = `${Number(date.slice(5, 7))}월 ${Number(date.slice(8, 10))}일`;
	return [
		`${md} ${name} 값(${valueText}), 어떤 상태인가요?`,
		`${name} 값이 이렇게 나온 가장 큰 원인이 뭐예요?`,
		`${name} 값을 좋게 하려면 앞으로 무엇을 바꿔야 해요?`
	];
}

export type MetricPrefillState =
	| { ok: true; prefill: MetricPrefill }
	| { ok: false; reason: 'bad_metric' | 'bad_date' | 'future'; slug: string | null };

/** C-08: `?metric=` 이 있을 때의 판정 — 대문자는 소문자로, 날짜가 없으면 오늘, 미래·형식 오류는 사유를 돌려준다. */
export function metricPrefillState(params: URLSearchParams, today: string): MetricPrefillState | null {
	const raw = params.get('metric');
	if (raw == null) return null;
	const slug = raw.trim().toLowerCase();
	if (!SLUG.test(slug)) return { ok: false, reason: 'bad_metric', slug: null };
	const date = params.get('date') || today;
	if (!DATE.test(date) || Number.isNaN(Date.parse(date))) return { ok: false, reason: 'bad_date', slug };
	if (date > today) return { ok: false, reason: 'future', slug };
	return { ok: true, prefill: { slug, date } };
}

/** C-08: 지표 프리필 실패 안내 — 활동 문구 대신 지표 사유와 복구 경로. */
export function metricPrefillError(reason: 'bad_metric' | 'bad_date' | 'future' | 'unknown_metric'): string {
	if (reason === 'future') return '아직 오지 않은 날짜의 지표는 물어볼 수 없어요. 오늘이나 지난 날짜로 열어 주세요.';
	if (reason === 'bad_date') return '날짜 형식이 맞지 않아요(YYYY-MM-DD).';
	return '알 수 없는 지표예요. 지표 목록에서 다시 골라 주세요.';
}
