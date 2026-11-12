// 활동 메트릭 탭 표기 보조(A-34 단위 한글화, A-35 부하 척도 안내). 순수 함수. 테스트: frontend/tests/activityListB2.test.mjs

/**
 * 레지스트리 영문 단위 → 화면 단위. score→'점', AU(임의 단위)→표기 없음, count 는 지표에 맞는 낱말.
 * 모르는 단위는 그대로 둔다. 지표 이름 자체의 한글화는 문구 확정(TXT-1) 대상이라 여기서 하지 않는다.
 */
export function unitLabel(unit: string, metricName = ''): string {
	if (unit === 'score') return '점';
	if (unit === 'AU') return '';
	if (unit === 'count' || unit === 'steps') {
		if (metricName.includes('step')) return '걸음';
		if (metricName.includes('floor')) return '층';
		return '회';
	}
	if (unit === 'min/wk') return '분/주';
	return unit;
}

/** 한 활동에서 서로 다른 방식으로 계산한 '부하' 계열 지표(척도가 서로 다름). */
export const LOAD_SCALE_METRICS = [
	'training_load', 'trimp', 'hrss', 'rtss', 'training_stress_score', 'suffer_score', 'relative_effort', 'wlei'
];

/** 부하 계열 지표가 2개 이상 같이 보이면 척도 차이 안내 한 줄, 아니면 ''(A-35). 문구는 TXT-1 확정. */
export function loadScaleNote(names: string[]): string {
	const n = new Set(names.filter((m) => LOAD_SCALE_METRICS.includes(m))).size;
	return n >= 2 ? `부하 지표 ${n}개는 계산 방식마다 척도가 달라 숫자끼리 크기를 비교할 수 없어요.` : '';
}
