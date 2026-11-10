// 메트릭 브라우저 검색 — 한글명·약어·영문 slug·라벨에 대한 부분 일치(대소문자 무시).
// M-29: 자주 쓰는 말(동의어)로도 찾는다 — 검색어가 동의어 키를 포함하면 그 지표 slug 도 맞는 것으로 본다.
import type { MetricBrowserEntry } from '$lib/types';

/** 검색어(소문자) → 해당 지표 slug. 공백은 무시하고 비교한다. 검색 보조용 목록(화면 문구 아님). */
export const SEARCH_SYNONYMS: Record<string, string[]> = {
	vo2: ['vo2max'],
	최대산소: ['vo2max'],
	회복: ['utrs', 'crs', 'body_battery_high', 'body_battery_low', 'sleep_body_battery_change', 'hrv_last_night', 'resting_hr', 'sleep_score'],
	컨디션: ['utrs', 'crs', 'training_readiness_score'],
	준비: ['utrs', 'crs', 'rri', 'training_readiness_score'],
	부상: ['cirs', 'acwr', 'lsi'],
	피로: ['atl', 'tsb', 'cirs'],
	체력: ['ctl', 'vo2max'],
	심박변이: ['hrv_last_night', 'hrv_weekly_avg', 'hrv_status'],
	잠: ['sleep_score', 'sleep_duration_sec'],
	예측: ['race_pred_5k_sec', 'race_pred_10k_sec', 'race_pred_half_sec', 'race_pred_marathon_sec', 'race_pred_vdot'],
	마라톤: ['race_pred_marathon_sec', 'marathon_shape'],
	효율: ['rec'],
	역치: ['eftp', 'lthr_self', 'lthr_ref', 'lt_speed_ref'],
	배터리: ['body_battery_high', 'body_battery_low', 'sleep_body_battery_change'],
	bb: ['body_battery_high', 'body_battery_low', 'sleep_body_battery_change']
};

function synonymSlugs(q: string): Set<string> {
	const key = q.replace(/\s+/g, '');
	const out = new Set<string>();
	for (const [word, slugs] of Object.entries(SEARCH_SYNONYMS)) {
		if (key.includes(word)) slugs.forEach((s) => out.add(s));
	}
	return out;
}

export function matchesMetric(m: Pick<MetricBrowserEntry, 'name' | 'label' | 'name_ko' | 'abbr'>, query: string): boolean {
	const q = query.trim().toLowerCase();
	if (!q) return true;
	if ([m.name, m.label, m.name_ko, m.abbr].some((v) => (v ?? '').toLowerCase().includes(q))) return true;
	return synonymSlugs(q).has(m.name);
}
