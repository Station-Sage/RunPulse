// 데이터 신선도(ADR-050) 표시 문구 — 서버가 내려준 text 를 그대로 쓴다(FRS-23). 테스트: tests/freshness.test.mjs
import type { FreshnessInfo, HoldReason } from './types/index';

/** 목록·게이지용 배지 문구(없으면 null). fresh/missing 은 서버가 badge 를 주지 않는다. */
export function freshnessBadgeText(fr: FreshnessInfo | null | undefined): string | null {
	return fr?.badge?.text || null;
}

/** 상세용 사유 문장들(서버 text). 누락 입력 이름은 missing_inputs 로 따로 보여준다(FRS-13). */
export function freshnessReasonTexts(fr: FreshnessInfo | null | undefined): string[] {
	return (fr?.reasons ?? []).map((r) => r.text).filter((t): t is string => !!t);
}

/** 상세용: 계산에서 빠진 입력 컬럼 이름. */
export function missingInputsText(fr: FreshnessInfo | null | undefined): string {
	return (fr?.missing_inputs ?? []).join(', ');
}

/** 히어로 보류 사유 한 줄(중립 회색). 없으면 null. */
export function holdText(reasons: HoldReason[] | null | undefined): string | null {
	const texts = (reasons ?? []).map((r) => r.text).filter(Boolean);
	return texts.length ? texts.join(' · ') : null;
}
