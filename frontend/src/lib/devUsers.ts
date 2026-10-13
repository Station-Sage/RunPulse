// 개발용 사용자 전환 — 순수 로직(화면 밖). 서버(`validate_uid`, SRV-13)가 최종 판정이며
// 여기 규칙은 입력 즉시 안내용 사본이다. 규칙을 바꾸면 서버와 함께 바꾼다.

const UID_RE = /^[A-Za-z0-9._%+@-]{1,254}$/;

export const UID_HINT = "영문·숫자와 . _ % + @ - 만, 1~254자, 맨 앞 '.' 불가";

/** 입력이 규칙에 맞지 않으면 안내 문구, 맞으면 null. 앞뒤 공백은 서버처럼 무시한다. */
export function uidProblem(raw: string): string | null {
	const v = raw.trim();
	if (!v) return '사용자 이름을 입력하세요';
	if (!UID_RE.test(v) || v.startsWith('.')) return UID_HINT;
	return null;
}

/** 목록 선택값과 새 사용자 입력 중 실제로 보낼 값 — 새 사용자 입력이 있으면 그것이 우선. */
export function pickUserId(selected: string, typed: string): string {
	return typed.trim() || selected.trim();
}

/** 전환 대상이 현재 사용자인가(불필요한 요청·새로고침 방지). */
export function isSameUser(target: string, current: string): boolean {
	return target.trim() === current;
}
