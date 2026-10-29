// A11Y 공통 4단계 — 테마 선호(시스템/라이트/다크) 저장·적용. 순수 함수 + 얇은 DOM 래퍼.
export type ThemePref = 'system' | 'light' | 'dark';
export const THEME_KEY = 'rp-theme';
export const THEME_COLORS = { dark: '#0f172a', light: '#f7f5f2' } as const;

export function isPref(v: unknown): v is ThemePref {
	return v === 'system' || v === 'light' || v === 'dark';
}

export function resolveTheme(pref: ThemePref, systemLight: boolean): 'light' | 'dark' {
	if (pref === 'system') return systemLight ? 'light' : 'dark';
	return pref;
}

// [dark meta content, light meta content]. 수동 선택이면 두 meta 모두 선택 테마 값으로 덮는다.
export function themeColorFor(pref: ThemePref): [string, string] {
	if (pref === 'light') return [THEME_COLORS.light, THEME_COLORS.light];
	if (pref === 'dark') return [THEME_COLORS.dark, THEME_COLORS.dark];
	return [THEME_COLORS.dark, THEME_COLORS.light];
}

export function readPref(): ThemePref {
	try {
		const v = localStorage.getItem(THEME_KEY);
		return isPref(v) ? v : 'system';
	} catch {
		return 'system';
	}
}

export function writePref(pref: ThemePref): void {
	try {
		if (pref === 'system') localStorage.removeItem(THEME_KEY);
		else localStorage.setItem(THEME_KEY, pref);
	} catch {
		/* 저장 불가(사생활 보호 모드 등) — 이번 방문에만 적용 */
	}
}

export function applyTheme(pref: ThemePref): void {
	const root = document.documentElement;
	if (pref === 'system') delete root.dataset.theme;
	else root.dataset.theme = pref;
	const [dark, light] = themeColorFor(pref);
	document.querySelector('meta[name="theme-color"][media*="dark"]')?.setAttribute('content', dark);
	document.querySelector('meta[name="theme-color"][media*="light"]')?.setAttribute('content', light);
}
