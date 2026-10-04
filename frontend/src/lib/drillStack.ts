// 드릴다운 스택 URL 동기화(§C3.3) — `?drill=m.slug1,m.slug2[@scope]` 쉼표 스택.
// scope 있는 토큰(D1d, 예: `m.tsb@2026-09-12`)은 Coach 근거 칩처럼 화면 기준일과
// 다른 날짜의 메트릭을 열 때 쓴다. scope 생략 시 DrillPanel의 기본 scopeId를 쓴다.
//
// SvelteKit의 pushState는 히스토리 항목의 URL 표시줄은 바꾸지만 `page.url`은 갱신하지
// 않는다(shallow routing 전용 — 실제로 변하는 건 `page.state`뿐). 그래서 두 값 다 쓴다:
// push 직후의 "지금" 값은 `page.state.drill`에서, 새로고침·딥링크 직후의 "처음" 값은
// `page.url`의 `drill` 쿼리에서 읽는다(`currentDrillStack` 참조).
import { pushState } from '$app/navigation';
import { page } from '$app/state';
import { DRILL_MAX_DEPTH, formatDrillToken, parseDrillStack, parseDrillToken, resolveDrillScope, tokenSlug } from './drillStackCore';

export { parseDrillStack, parseDrillToken, resolveDrillScope, tokenSlug };

export function currentDrillStack(): string[] {
	return page.state.drill ?? parseDrillStack(page.url);
}

// 패널 밖의 독립된 진입점(EvidenceQuote 등)이 부른다 — 스택을 이 슬러그
// 하나로 새로 연다. 이미 다른 지표가 열려 있어도 "그 안"으로 들어가는 게 아니라
// 새 조회이므로 스택을 비우고 시작한다.
export function openDrill(slug: string, scope?: string) {
	const token = formatDrillToken(slug, scope);
	const stack = currentDrillStack();
	if (stack.length === 1 && stack[0] === token) return;
	const url = new URL(page.url);
	url.searchParams.set('drill', token);
	pushState(url, { drill: [token] });
}

// 패널 안(BreakdownView 행)의 `drill` 탭이 부른다 — 지금 스택 위에 한 단계 쌓는다(§C3.1 최대 3단).
export function pushDrill(slug: string, scope?: string) {
	const stack = currentDrillStack();
	const token = formatDrillToken(slug, scope);
	if (stack.length >= DRILL_MAX_DEPTH || stack.at(-1) === token) return;
	const next = [...stack, token];
	const url = new URL(page.url);
	url.searchParams.set('drill', next.join(','));
	pushState(url, { drill: next });
}

export function popDrill() {
	if (currentDrillStack().length > 0) history.back();
}

export function closeDrill() {
	const depth = currentDrillStack().length;
	if (depth > 0) history.go(-depth);
}
