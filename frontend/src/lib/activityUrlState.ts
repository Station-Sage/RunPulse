// 활동 상세 요약의 URL 보기 상태 파서 — `?seg=`는 1 이상의 정수만 받는다.
export function parseSeg(raw: string | null): number | null {
	if (!raw || !/^\d+$/.test(raw)) return null;
	const n = Number(raw);
	return n >= 1 ? n : null;
}
