// D1c(§C4 예외): 활동 히어로·랩 표는 소수 2자리, 그 외(목록·요약·Today)는 1자리.
export function formatDistance(m: number, decimals: 1 | 2 = 1): string {
	if (m < 1000) return `${Math.round(m)}m`;
	return `${(m / 1000).toFixed(decimals)}km`;
}

export function formatDuration(sec: number): string {
	const h = Math.floor(sec / 3600);
	const m = Math.floor((sec % 3600) / 60);
	const s = Math.floor(sec % 60);
	const mm = String(m).padStart(2, '0');
	const ss = String(s).padStart(2, '0');
	return h > 0 ? `${h}:${mm}:${ss}` : `${m}:${ss}`;
}

// 초를 먼저 반올림해야 359.6 → "5:60"이 아니라 "6:00"이 된다.
function paceMmSs(secPerKm: number): string {
	const total = Math.round(secPerKm);
	return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
}

export function formatPace(secPerKm: number): string {
	return `${paceMmSs(secPerKm)}/km`;
}

/**
 * 원시 단위 값을 러너가 읽을 수 있는 표현으로 변환.
 * - sec   → h:mm:ss / m:ss 형식, unit ''
 * - sec/km → m:ss/km 형식, unit ''
 * - m (≥1000) → km 1자리, unit 'km'
 * - 그 외: 100 이상은 정수, 미만은 소수 1자리, unit 그대로
 */
/** 계획 페이스 범위(초/km, min=빠른 쪽) → '6:05–6:45/km'. 한쪽만 있으면 '>6:05/km'·'<6:45/km', 둘 다 없으면 ''. */
export function formatPaceRange(min: number | null, max: number | null): string {
	if (min == null && max == null) return '';
	const fmt = paceMmSs;
	if (min != null && max != null) return `${fmt(min)}–${fmt(max)}/km`;
	return min != null ? `>${fmt(min)}/km` : `<${fmt(max!)}/km`;
}

/** 계획 진행 라벨: '3주차 / 9주', 시작 전이면 '시작 전 (2주 뒤)'. planWeeks 없으면 '3주차'. */
export function weekProgressLabel(weekIndex: number, planWeeks?: number | null): string {
	if (weekIndex < 1) return `시작 전 (${1 - weekIndex}주 뒤)`;
	return planWeeks ? `${weekIndex}주차 / ${planWeeks}주` : `${weekIndex}주차`;
}

/** 값 자체가 시간/페이스 표기(h:mm:ss, m:ss)로 단위가 내장된 경우 단위 라벨을 숨긴다. */
export function displayUnit(unit: string | null | undefined): string {
	if (!unit || unit === 'sec' || unit === 'sec/km') return '';
	return unit;
}

export function formatUnitValue(value: number, unit: string): { display: string; unit: string } {
	if (unit === 'sec') {
		return { display: formatDuration(value), unit: '' };
	}
	if (unit === 'sec/km') {
		return { display: formatPace(value), unit: '' };
	}
	if (unit === 'm' && value >= 1000) {
		return { display: (value / 1000).toFixed(1), unit: 'km' };
	}
	// 정수는 그대로(58 → '58', '58.0' 아님), 100 이상은 정수, 그 외 소수 1자리(끝 0 제거) — 부동소수 잡음(26.0799…)도 여기서 정리
	const display = Number.isInteger(value)
		? String(value)
		: Math.abs(value) >= 100
			? String(Math.round(value))
			: String(Number(value.toFixed(1)));
	return { display, unit };
}

// §C4 — 음수는 하이픈이 아니라 U+2212(수학 마이너스)를 쓴다.
export const MINUS = '−';

/** 부하(CTL/ATL) — 소수 1자리, 부호 없음. */
export function formatLoad(value: number): string {
	return value.toFixed(1);
}

/** 폼(TSB) 요약·칩·게이지 — 부호 있는 정수. */
export function formatForm(value: number): string {
	const rounded = Math.round(value);
	if (rounded === 0) return '0';
	return rounded > 0 ? `+${rounded}` : `${MINUS}${Math.abs(rounded)}`;
}

/** 폼(TSB) 분해 공식 — 소수 1자리, 부호 있음. */
export function formatFormDetail(value: number): string {
	const rounded = Math.round(value * 10) / 10;
	if (rounded === 0) return '0';
	return rounded > 0 ? `+${rounded.toFixed(1)}` : `${MINUS}${Math.abs(rounded).toFixed(1)}`;
}

/** 비율(ACWR 등) — 소수 2자리, 부호 없음. */
export function formatRatio(value: number): string {
	return value.toFixed(2);
}

/** 백분율 — 정수 %. */
export function formatPercent(value: number): string {
	return `${Math.round(value)}%`;
}

/** 백분위 — 'p78'. */
export function formatPercentile(value: number): string {
	return `p${Math.round(value)}`;
}

/** 점수(0–100) — 정수. */
export function formatScore(value: number): string {
	return String(Math.round(value));
}

/** 심박 — 정수 bpm. */
export function formatHeartRate(value: number): string {
	return `${Math.round(value)} bpm`;
}

/** 변화량 — 항상 부호(화살표·색·좋고 나쁨 판정은 호출부 몫). decimals=0이면 정수(층·걸음 등), >0이면 소수. */
export function formatChange(value: number, decimals = 0): string {
	const rounded = Number(value.toFixed(decimals));
	if (rounded === 0) return decimals > 0 ? `0` : '0';
	const abs = Math.abs(rounded).toFixed(decimals);
	return rounded > 0 ? `+${abs}` : `${MINUS}${abs}`;
}

/** 시간 차 — 1분 미만은 반올림돼 '0분', 그 외 'n분'(±). 초 단위 정밀도는 D2 전용. */
export function formatTimeDiff(sec: number): string {
	const minutes = Math.round(sec / 60);
	if (minutes === 0) return '0분';
	return minutes > 0 ? `+${minutes}분` : `${MINUS}${Math.abs(minutes)}분`;
}

/**
 * 예측 기록 — 신뢰도 <0.5면 'h:mm (h:mm–h:mm)', ≥0.5면 'h:mm:ss'(§C4).
 * rangeSec: [최속, 최느림] 초.
 */
export function formatPrediction(
	sec: number,
	confidence: number,
	rangeSec?: readonly [number, number] | null
): string {
	if (confidence >= 0.5 || !rangeSec) return formatDuration(sec);
	const shortHm = (s: number) => {
		const total = Math.round(s / 60);
		return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
	};
	return `${shortHm(sec)} (${shortHm(rangeSec[0])}–${shortHm(rangeSec[1])})`;
}

export function formatDate(isoStr: string): string {
	return isoStr.slice(0, 10);
}

// SQLite datetime('now')는 UTC인데 'YYYY-MM-DD HH:MM:SS'로 시간대 표기가 없어 JS가 로컬 시각으로
// 잘못 해석한다(KST면 9시간 어긋남). 시간대 표기가 없으면 UTC로 간주해 파싱한다.
export function parseDbTimestamp(s: string): Date {
	const hasZone = /(Z|[+-]\d{2}:?\d{2})$/.test(s);
	return new Date(hasZone ? s : s.replace(' ', 'T') + 'Z');
}

export function formatRelativeTime(isoStr: string): string {
	const diff = Date.now() - parseDbTimestamp(isoStr).getTime();
	const minutes = Math.floor(diff / 60_000);
	if (minutes < 2) return '방금 전';
	if (minutes < 60) return `${minutes}분 전`;
	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${hours}시간 전`;
	const days = Math.floor(hours / 24);
	if (days < 7) return `${days}일 전`;
	const weeks = Math.floor(days / 7);
	if (weeks < 5) return `${weeks}주 전`;
	const months = Math.floor(days / 30);
	return `${months}개월 전`;
}

export const WORKOUT_LABELS: Record<string, string> = {
	rest: '휴식',
	recovery: '회복',
	easy: '쉬운 달리기',
	long: '장거리',
	long_run: '장거리',
	steady: '스테디',
	tempo: '템포',
	interval: '인터벌',
	marathon: '마라톤 페이스',
	long_mp: '롱런(MP)',
	threshold: '역치',
	repetition: '레피티션',
	sprint: '스프린트',
	race: '레이스'
};

export function workoutLabel(type: string): string {
	return WORKOUT_LABELS[type] ?? type;
}

const WEEKDAY_KO = ['일', '월', '화', '수', '목', '금', '토'];

/** 날짜(본문) — '9월 27일 (일)'. */
export function formatDateLong(isoDate: string): string {
	const d = new Date(`${isoDate.slice(0, 10)}T00:00:00Z`);
	return `${d.getUTCMonth() + 1}월 ${d.getUTCDate()}일 (${WEEKDAY_KO[d.getUTCDay()]})`;
}

/** 날짜(짧게) — '9/27(일)'. */
export function formatDateShort(isoDate: string): string {
	const d = new Date(`${isoDate.slice(0, 10)}T00:00:00Z`);
	return `${d.getUTCMonth() + 1}/${d.getUTCDate()}(${WEEKDAY_KO[d.getUTCDay()]})`;
}

export function formatRelativeDay(isoDate: string): string {
	const date = new Date(isoDate);
	const today = new Date();
	const diffDays = Math.round(
		(Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()) -
			Date.UTC(date.getFullYear(), date.getMonth(), date.getDate())) /
			86_400_000
	);
	if (diffDays === 0) return '오늘';
	if (diffDays === 1) return '어제';
	if (diffDays > 1) return `${diffDays}일 전`;
	return date.toLocaleDateString('ko-KR');
}

export interface MetricFormatMeta {
	format?: string;
	unit?: string;
	decimal_places?: number;
}

/** registry `format` → §C4 포맷 함수 디스패치(목록·상세·차트 공용). 값 없으면 '—'. */
export function formatMetric(meta: MetricFormatMeta, value: number | null | undefined): string {
	if (value == null || !Number.isFinite(value)) return '—';
	switch (meta.format) {
		case 'race_time':
		case 'duration':
			return formatDuration(value);
		case 'pace':
			return formatPace(value);
		case 'signed':
			return formatForm(value);
		case 'percent':
			return formatPercent(value);
		case 'score':
			return formatScore(value);
		default: {
			const dp = meta.decimal_places;
			if (dp == null) return formatUnitValue(value, meta.unit ?? '').display;
			return dp === 0 ? String(Math.round(value)) : value.toFixed(dp);
		}
	}
}
