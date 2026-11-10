// 메트릭 브라우저(/library/metrics) 목록 표시 순수 헬퍼 — 값·단위(M-06·M-10), Provider 필터(M-13).
// 테스트: frontend/tests/metricDetailC.test.mjs
import { formatMetric } from './format.ts';
import { metricUnitText } from './metricDetail.ts';
import type { MetricBrowserCategory, MetricBrowserEntry } from './types/index.ts';

/** provider 가 없는 지표(웰니스 기록 — Garmin·Intervals 가 같은 표에 합쳐 저장)를 고르는 필터 키. */
export const WELLNESS_PROVIDER = '_wellness';

/** 지표의 Provider 필터 키 — 'garmin:fr965' → 'garmin', 없으면 WELLNESS_PROVIDER. */
export function providerKey(m: Pick<MetricBrowserEntry, 'provider'>): string {
	return (m.provider ?? '').split(':')[0] || WELLNESS_PROVIDER;
}

/** 필터 칩 목록: 실제 provider(정렬) + 웰니스 기록(있을 때 맨 뒤). */
export function providerKeys(categories: MetricBrowserCategory[]): string[] {
	const keys = new Set(categories.flatMap((c) => c.metrics.map(providerKey)));
	const real = [...keys].filter((k) => k !== WELLNESS_PROVIDER).sort();
	return keys.has(WELLNESS_PROVIDER) ? [...real, WELLNESS_PROVIDER] : real;
}

/** 선택한 provider 에 맞는지('all'은 전부). */
export function matchesProvider(m: Pick<MetricBrowserEntry, 'provider'>, selected: string): boolean {
	return selected === 'all' || providerKey(m) === selected;
}

/** 카드 값 — 상세와 같은 formatMetric(M-10). 문자열 값은 그대로, 없으면 '—'. */
export function cardValue(m: MetricBrowserEntry): string {
	if (m.value == null) return '—';
	if (typeof m.value === 'string') return m.value;
	return formatMetric(m, Number(m.value));
}

/** 카드 단위 — 형식이 단위를 품으면 숨김(M-06 '66% %' 방지), 그 외 한글 단위. */
export function cardUnit(m: MetricBrowserEntry): string {
	if (m.value == null || typeof m.value === 'string') return '';
	return metricUnitText(m, m.name);
}
