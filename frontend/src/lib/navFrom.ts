/** 내비게이션 출처(afterNavigate 의 `from`)를 null 안전하게 읽는 헬퍼. */

/**
 * SvelteKit 은 SPA 최초 진입(enter) 시 `from` 이 null 이거나 `from.url` 이 null 이다
 * (kit 근거: enter 타입의 Navigation.from.url 은 null 가능). `from.url.pathname` 직접 접근은 TypeError.
 */
export function navFromPath(from: { url?: URL | null } | null | undefined): string | null {
	return from?.url?.pathname ?? null;
}
