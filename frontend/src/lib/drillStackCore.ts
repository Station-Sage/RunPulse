// 드릴다운 스택 URL 파싱 — SvelteKit 의존 없는 순수 함수만(테스트 가능하게 분리).
// 토큰 문법(§C3.3 D1d): `m.{slug}` 또는 활동 scope가 있으면 `m.{slug}@{scope}`.
// scope는 `YYYY-MM-DD`(daily) 또는 `a{활동id}`(activity) — 생략하면 호출부가 화면 기준일로 채운다.
export const DRILL_MAX_DEPTH = 3;

export interface DrillTokenParts {
	slug: string;
	scope?: string;
}

export function parseDrillStack(url: URL): string[] {
	const raw = url.searchParams.get('drill');
	if (!raw) return [];
	return raw
		.split(',')
		.map((t) => t.trim())
		.filter(Boolean);
}

export function parseDrillToken(token: string): DrillTokenParts {
	const body = token.startsWith('m.') ? token.slice(2) : token;
	const at = body.indexOf('@');
	if (at === -1) return { slug: body };
	return { slug: body.slice(0, at), scope: body.slice(at + 1) || undefined };
}

// 특수 시트 토큰(`x.taper`) — 지표 분해가 아닌 전용 시트. 스택·URL 규칙은 지표 토큰과 같다.
export function isSpecialToken(token: string): boolean {
	return token.startsWith('x.');
}

export function formatDrillToken(slug: string, scope?: string): string {
	if (isSpecialToken(slug)) return slug;
	return scope ? `m.${slug}@${scope}` : `m.${slug}`;
}

// 하위 호환 별칭 — 슬러그만 필요한 기존 소비처용.
export function tokenSlug(token: string): string {
	return parseDrillToken(token).slug;
}

// scope 문자열 → API scope. `a17414` → activity/17414, 그 외는 기본 scope 종류를 따른다.
export function resolveDrillScope(
	scope: string | undefined,
	defaultType: string,
	defaultId: string
): { scopeType: string; scopeId: string } {
	if (!scope) return { scopeType: defaultType, scopeId: defaultId };
	const m = /^a(\d+)$/.exec(scope);
	return m ? { scopeType: 'activity', scopeId: m[1] } : { scopeType: defaultType, scopeId: scope };
}
