// 분기별 페이지 h1 결정 — 자식이 h1 을 그리는 상태면 null(위임), 아니면 화면 제목.
export type HeadingState = 'ok' | 'empty' | 'failed';

export function pageHeading(
	state: HeadingState,
	title: string,
	childOwns: readonly HeadingState[]
): string | null {
	return childOwns.includes(state) ? null : title;
}
