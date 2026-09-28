// 드릴다운 스택 URL 동기화(§C3.3) — `?drill=m.slug1,m.slug2` 쉼표 스택.
// 이번 라운드는 scope 없는 `m.{slug}` 토큰만 다룬다(활동 scope `@a{id}`는 D1d, 2-5 범위 밖).
//
// SvelteKit의 pushState는 히스토리 항목의 URL 표시줄은 바꾸지만 `page.url`은 갱신하지
// 않는다(shallow routing 전용 — 실제로 변하는 건 `page.state`뿐). 그래서 두 값 다 쓴다:
// push 직후의 "지금" 값은 `page.state.drill`에서, 새로고침·딥링크 직후의 "처음" 값은
// `page.url`의 `drill` 쿼리에서 읽는다(`currentDrillStack` 참조).
import { pushState } from '$app/navigation';
import { page } from '$app/state';
import { DRILL_MAX_DEPTH, parseDrillStack, tokenSlug } from './drillStackCore';

export { parseDrillStack, tokenSlug };

export function currentDrillStack(): string[] {
	return page.state.drill ?? parseDrillStack(page.url);
}

// 패널 밖의 독립된 진입점(ScoreRing 등)이 부른다 — 스택을 이 슬러그 하나로 새로 연다.
// 이미 다른 지표가 열려 있어도 "그 안"으로 들어가는 게 아니라 새 조회이므로 스택을 비우고 시작한다.
export function openDrill(slug: string) {
	const token = `m.${slug}`;
	if (currentDrillStack().length === 1 && currentDrillStack()[0] === token) return;
	const url = new URL(page.url);
	url.searchParams.set('drill', token);
	pushState(url, { drill: [token] });
}

// 패널 안(BreakdownView 행)의 `drill` 탭이 부른다 — 지금 스택 위에 한 단계 쌓는다(§C3.1 최대 3단).
export function pushDrill(slug: string) {
	const stack = currentDrillStack();
	const token = `m.${slug}`;
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
