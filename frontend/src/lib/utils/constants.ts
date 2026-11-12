/**
 * 전역 상수 및 메시지
 * TXT-1 확정 문구 (모두 한 곳에 모아서 관리)
 */

/**
 * SyncStatusPill 관련 메시지
 */
export const SYNC_STATUS_MESSAGES = {
	// stale (신선도 경과)
	staleTitle: '▲ Garmin 확인 필요',
	staleBody: '입력이 오래됐어요',

	// partial (일부 데이터 결측)
	partialBody: '일부 데이터 없이 계산',

	// 동기화 필요 화면에서만 표시
	// source_missing은 숨김 (welcome/404/error 화면)
	sourceMissingBadge: 'Garmin 필요',
};

/**
 * 404/오류 페이지 메타 정보
 */
export const ERROR_PAGE_META = {
	notFoundTitle: '페이지를 찾을 수 없습니다',
	notFoundDescription: '404',
	serverErrorTitle: '오류가 발생했습니다',
	serverErrorDescription: '500',
};

/**
 * 데모 모드 메시지
 */
export const DEMO_MODE_MESSAGES = {
	writeBlocked: '데모 모드에서는 변경할 수 없습니다',
	readOnlyMode: 'Read-only mode',
};

/**
 * 로딩 상태 메시지
 */
export const LOADING_MESSAGES = {
	fetchingData: '불러오는 중이에요',
	dataUnavailable: '데이터를 불러오지 못했어요',
	navigating: '화면을 불러오는 중이에요',
};

/**
 * 오프라인 상태 메시지
 */
export const OFFLINE_MESSAGES = {
	offline: '인터넷 연결이 끊겼어요. 연결되면 다시 불러올 수 있어요.',
	restored: '다시 연결됐어요.',
};

/**
 * 입력 검증 메시지 (Range/constraint 위반)
 */
export const VALIDATION_MESSAGES = {
	invalidMonth: '잘못된 월입니다',
	invalidYear: '잘못된 연도입니다',
	invalidPage: '잘못된 페이지입니다',
	invalidActivityId: '잘못된 활동 ID입니다',
	invalidSort: '잘못된 정렬입니다',
	invalidRange: '잘못된 기간입니다',
	fieldTooLong: '입력이 너무 깁니다',
	fieldRequired: '필수 항목입니다',
};

/**
 * API 에러 메시지 (서버 원문 노출 방지, 일반화)
 */
export const API_ERROR_MESSAGES = {
	networkError: '네트워크 오류가 발생했습니다',
	serverError: '서버 오류가 발생했습니다',
	badRequest: '잘못된 요청입니다',
	notFound: '찾을 수 없습니다',
	unauthorized: '인증이 필요합니다',
};

/**
 * 환경 감지 메시지 (stale/partial 관련)
 */
export const FRESHNESS_MESSAGES = {
	// FRS-4에 따른 문구
	staleMessage: '입력이 오래됐어요',
	partialMessage: '일부 데이터 없이 계산했어요',
	boostHoldMessage: 'HRV·바디배터리 데이터가 없어 강도 상향은 보류했어요',
	cautionHeader: '최근 데이터가 부족해 참고용이에요',
	basedOnDate: 'MM-DD 기록 기준',
};

/**
 * 비러닝 활동 라벨
 */
export const NON_RUNNING_LABELS = {
	swimming: '수영',
	strength: '근력',
	walking: '걷기',
	cycling: '자전거',
	elliptical: '타원형',
	yoga: '요가',
	hiit: '하이 인텐시티',
	other: '기타',
};

/**
 * 온보딩 단계 라벨
 */
export const ONBOARDING_STEPS = {
	step1: '단계 1',
	step2: '단계 2',
	step3: '단계 3',
	step4: '단계 4',
};
