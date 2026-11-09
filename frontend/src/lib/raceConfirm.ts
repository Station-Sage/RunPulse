// 대회 확인 목록 순수 헬퍼(T-13·T-14). 테스트: tests/raceConfirm.test.mjs
import type { RaceCandidate, RaceEffort } from './types/index.ts';

/**
 * 탭한 노력도 → 저장할 값. 이미 선택된 버튼을 다시 눌러도 해제하지 않는다(더블탭이 PUT→DELETE 로
 * '미선택'이 되던 문제, T-13). 해제는 별도 '표시 해제' 버튼(null)으로만 한다. 바뀔 게 없으면 undefined.
 */
export function nextEffort(prev: RaceEffort | null, tapped: RaceEffort | null): RaceEffort | null | undefined {
	return prev === tapped ? undefined : tapped;
}

/** 후보 판단 보조 문구 — 왜 후보인지·이름과 거리가 다른지(T-14). 없으면 null. */
export function candidateHint(c: Pick<RaceCandidate, 'why' | 'distance_mismatch'>): string | null {
	const parts: string[] = [];
	if (c.why === 'event_type') parts.push('기기에서 대회로 표시한 활동');
	if (c.distance_mismatch) parts.push('이름의 종목과 거리가 달라요 — 대회 전체 기록이 아닐 수 있어요');
	return parts.length ? parts.join(' · ') : null;
}
