// frontend/src/lib/healthNotice.ts
// 데이터 건강 알림 판정 — 부하(TRIMP) 누락이 많을 때만 안내. 테스트: frontend/tests/healthNotice.test.mjs

export interface LoadCoverage {
	window_days: number;
	runs: number;
	missing: number;
	missing_ratio: number;
}

/** 누락 3건 이상이고 20% 이상일 때만 문구 반환, 아니면 null. */
export function loadCoverageNotice(h: LoadCoverage | null | undefined): string | null {
	if (!h || h.missing < 3 || h.missing_ratio < 0.2) return null;
	return `최근 ${h.window_days}일 러닝 ${h.runs}회 중 ${h.missing}회의 훈련 부하가 계산되지 않아 체력·피로·폼 수치가 실제보다 낮게 나올 수 있어요. 동기화를 실행하면 자동으로 보정됩니다.`;
}
