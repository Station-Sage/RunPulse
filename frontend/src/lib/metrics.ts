// 활동 메트릭 표시 공용 헬퍼 — 요약/메트릭 탭이 같이 쓴다.
import type { ActivityMetric } from '$lib/types';
import { formatPace } from '$lib/format';
// metric_registry.METRIC_CATEGORIES(16 도메인)의 한글 라벨 — 키 순서가 곧 메트릭 탭의 표시 순서.
export const METRIC_CATEGORY_LABELS: Record<string, string> = {
	hr: '심박',
	pace: '페이스',
	running_dynamics: '러닝 다이내믹스',
	power: '파워',
	load: '부하',
	efficiency: '효율성',
	capacity: '체력/역량',
	prediction: '예측',
	volume: '운동량',
	weather: '날씨/환경',
	body: '신체',
	sleep: '수면',
	stress: '스트레스',
	readiness: '준비도',
	meta: '메타/분류',
	athlete: '선수 설정',
	_unmapped: '미매핑 (개발용)'
};
export function categoryLabel(key: string): string {
	return METRIC_CATEGORY_LABELS[key] ?? key;
}
// 알려진 카테고리는 위 순서, 모르는 카테고리는 그 뒤에 이름순.
export function sortCategories(keys: string[]): string[] {
	const known = Object.keys(METRIC_CATEGORY_LABELS);
	const rank = (k: string) => {
		const i = known.indexOf(k);
		return i === -1 ? known.length : i;
	};
	return [...keys].sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
}
// 페이스 계열(초/km)은 m:ss/km, 그 외 수치는 소수 1자리, 수치가 없으면 텍스트 값, 그것도 없으면 '—'.
export function formatMetricValue(m: ActivityMetric): string {
	if (m.numeric_value == null) return m.text_value ?? '—';
	const v = m.numeric_value;
	if (m.metric_name.includes('pace') || m.unit === 'sec/km') return formatPace(v);
	return Number.isInteger(v) ? String(v) : v.toFixed(1);
}
// formatMetricValue가 단위까지 붙이는 페이스 계열과 json 단위는 단위 표기 없음.
export function metricUnit(m: ActivityMetric): string {
	if (m.metric_name.includes('pace') || m.unit === 'sec/km' || m.unit === 'json') return '';
	return m.unit;
}

// 03c-library.md 3-C "핵심 메트릭" — 우선순위 이름 목록에서 값이 있는 것만 앞에서부터 고른다.
// avg_pace_sec_km/avg_hr는 요약 상단 통계 바가 이미 보여주므로 여기서는 제외(03c의 Pace·HR avg 칸을 통계 바가 대신함).
export const KEY_METRIC_NAMES = [
	'max_hr',
	'avg_cadence',
	'training_stress_score',
	'training_load',
	'training_effect_aerobic',
	'vo2max_activity',
	'efficiency_factor',
	'aerobic_decoupling',
	'avg_ground_contact_time_ms',
	'avg_stride_length_cm',
	'normalized_power',
	'relative_effort',
	'vdot'
];
export function pickKeyMetrics(
	byCategory: Record<string, ActivityMetric[]>,
	limit = 8
): ActivityMetric[] {
	const byName = new Map<string, ActivityMetric>();
	for (const items of Object.values(byCategory)) {
		for (const m of items) {
			if (m.numeric_value != null && !byName.has(m.metric_name)) byName.set(m.metric_name, m);
		}
	}
	return KEY_METRIC_NAMES.map((n) => byName.get(n))
		.filter((m): m is ActivityMetric => m != null)
		.slice(0, limit);
}
export interface HrZoneShare {
	zone: number;
	sec: number;
	pct: number;
}
// hr_zone_1..5_sec → 존별 체류 시간·비율. 존 메트릭이 없거나 합계가 0이면 null. provider는 첫 존 메트릭의 소스.
export function hrZoneShares(
	byCategory: Record<string, ActivityMetric[]>
): { zones: HrZoneShare[]; provider: string | null } | null {
	const all = Object.values(byCategory).flat();
	const secs = [1, 2, 3, 4, 5].map((z) => all.find((m) => m.metric_name === `hr_zone_${z}_sec`));
	const total = secs.reduce((n, m) => n + (m?.numeric_value ?? 0), 0);
	if (total <= 0) return null;
	return {
		zones: secs.map((m, i) => {
			const sec = m?.numeric_value ?? 0;
			return { zone: i + 1, sec, pct: Math.round((sec / total) * 100) };
		}),
		provider: secs.find((m) => m != null)?.provider ?? null
	};
}
