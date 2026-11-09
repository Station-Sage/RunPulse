/**
 * URL과 날짜 정규화 공용 유틸
 * - 잘못된 month/year 정규화
 * - URL 상태 replaceState
 * - 입력값 범위 검증
 */

export interface DateParams {
	year: number;
	month: number;
}

/**
 * 월/연도 파라미터를 정규화
 * @param year 연도 (범위: 현재-10년 ~ 현재+5년)
 * @param month 월 (범위: 1-12, 벗어나면 현재 월로)
 * @returns 정규화된 {year, month}
 */
export function normalizeDateParams(year?: string | number, month?: string | number): DateParams {
	const today = new Date();
	const currentYear = today.getFullYear();
	const currentMonth = today.getMonth() + 1;

	// 연도 정규화
	let normalizedYear = currentYear;
	if (year !== undefined && year !== null) {
		const parsed = typeof year === 'string' ? parseInt(year, 10) : year;
		if (!isNaN(parsed) && parsed >= currentYear - 10 && parsed <= currentYear + 5) {
			normalizedYear = parsed;
		}
	}

	// 월 정규화
	let normalizedMonth = currentMonth;
	if (month !== undefined && month !== null) {
		const parsed = typeof month === 'string' ? parseInt(month, 10) : month;
		if (!isNaN(parsed) && parsed >= 1 && parsed <= 12) {
			normalizedMonth = parsed;
		}
	}

	return { year: normalizedYear, month: normalizedMonth };
}

/**
 * 잘못된 URL 파라미터를 정규 URL로 변경하고 replaceState
 * @param currentUrl 현재 URL
 * @param correctedUrl 정규 URL
 */
export function replaceHistoryIfInvalid(currentUrl: string, correctedUrl: string): void {
	if (typeof window !== 'undefined' && currentUrl !== correctedUrl) {
		window.history.replaceState(null, '', correctedUrl);
	}
}

/**
 * 페이지 파라미터 검증
 * @param page 페이지 번호
 * @param maxPages 최대 페이지
 * @returns 유효한 페이지 또는 1
 */
export function validatePageParam(page?: string | number, maxPages = 1): number {
	if (page === undefined || page === null) return 1;
	const parsed = typeof page === 'string' ? parseInt(page, 10) : page;
	if (isNaN(parsed) || parsed < 1) return 1;
	if (maxPages > 0 && parsed > maxPages) return maxPages;
	return parsed;
}

/**
 * 소트 파라미터 검증
 * @param sort 소트 값
 * @param allowed 허용된 소트 값 목록
 * @returns 유효한 소트 값 또는 기본값
 */
export function validateSortParam(sort?: string, allowed: string[] = ['date', 'distance', 'pace']): string {
	if (sort && allowed.includes(sort)) return sort;
	return allowed[0];
}

/**
 * 범위 파라미터 (from/to) 정규화
 * @param from 시작 파라미터 (ISO 문자열 또는 empty)
 * @param to 끝 파라미터
 * @returns 정규화된 {from, to} 또는 빈 문자열
 */
export function normalizeRangeParams(from?: string, to?: string): { from?: string; to?: string } {
	const result: { from?: string; to?: string } = {};

	// from 검증: ISO 날짜 형식 또는 비우기
	if (from && /^\d{4}-\d{2}-\d{2}$/.test(from)) {
		result.from = from;
	}

	// to 검증: ISO 날짜 형식 또는 비우기
	if (to && /^\d{4}-\d{2}-\d{2}$/.test(to)) {
		result.to = to;
	}

	return result;
}

/**
 * 활동 ID 검증
 * @param id ID 문자열
 * @returns 정수 ID 또는 undefined
 */
export function validateActivityId(id?: string | number): number | undefined {
	if (id === undefined || id === null) return undefined;
	const parsed = typeof id === 'string' ? parseInt(id, 10) : id;
	return isNaN(parsed) || parsed <= 0 ? undefined : parsed;
}

/**
 * 메트릭 슬러그 검증
 * @param slug 메트릭 슬러그
 * @returns 유효성
 */
export function isValidMetricSlug(slug?: string): boolean {
	if (!slug) return false;
	return /^[a-z_]+$/.test(slug);
}

export interface MonthParam {
	year: number;
	month: number;
	/** 정규 표기 `YYYY-MM` — 입력과 다르면 화면이 이 값으로 URL 을 바꾼다. */
	ym: string;
}

/**
 * `YYYY-MM` 경로 파라미터 정규화 — 형식이 틀리거나 미래 달이면 이번 달(미래 기간 차단).
 * @param raw 경로 값
 * @param now 기준 시각(테스트 주입용)
 */
export function normalizeMonthParam(raw: string, now: Date = new Date()): MonthParam {
	const cy = now.getFullYear();
	const cm = now.getMonth() + 1;
	const m = /^(\d{4})-(\d{2})$/.exec(raw);
	let year = cy;
	let month = cm;
	if (m && +m[2] >= 1 && +m[2] <= 12 && +m[1] >= 2000) {
		const future = +m[1] > cy || (+m[1] === cy && +m[2] > cm);
		if (!future) {
			year = +m[1];
			month = +m[2];
		}
	}
	return { year, month, ym: `${year}-${String(month).padStart(2, '0')}` };
}
