import type { SemanticStatus } from '$lib/types';

// dashboard_service._LEVEL_THRESHOLDS의 레이블 그대로 매핑한다(src/services/dashboard_service.py).
// UTRS(higher_is_better=True, src/metrics/utrs.py)와 CIRS(higher_is_better=False — "부상
// 위험 지수", src/metrics/cirs.py)는 값이 높을 때의 의미가 반대라 같은 레이블도 반대로 매핑한다.
const UTRS_LEVELS: Record<string, SemanticStatus> = {
	'매우 좋음': 'excellent',
	양호: 'good',
	보통: 'neutral',
	낮음: 'caution',
	'매우 낮음': 'poor'
};

const CIRS_LEVELS: Record<string, SemanticStatus> = {
	'매우 높음': 'poor',
	높음: 'caution',
	보통: 'neutral',
	낮음: 'good',
	'매우 낮음': 'excellent'
};

export function readinessStatus(
	metric: 'utrs' | 'cirs',
	level: string | null | undefined
): SemanticStatus {
	if (!level) return 'neutral';
	return (metric === 'utrs' ? UTRS_LEVELS : CIRS_LEVELS)[level] ?? 'neutral';
}

// today_service._TSB_THRESHOLDS(src/services/today_service.py)와 같은 경계값.
export function tsbStatus(tsb: number | null): SemanticStatus {
	if (tsb === null) return 'neutral';
	if (tsb >= 15) return 'excellent';
	if (tsb >= 5) return 'good';
	if (tsb >= -10) return 'neutral';
	if (tsb >= -20) return 'caution';
	return 'poor';
}
