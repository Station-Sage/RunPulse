// 뒤로가기 규칙(B-3) — ?from= 이 앱 내부 경로이면 거기로, 아니면 부모 경로로. 외부 URL·'//' 는 무시한다(open-redirect 방지).
export const BACK_GLYPH = '‹';

/** 앱 내부 경로만 통과. '/'로 시작하되 '//'·'/\\'·제어문자·스킴은 거부. base 가 붙어 있으면 떼어 낸다. */
export function safeInternalPath(raw: string | null | undefined, base = ''): string | null {
	if (!raw) return null;
	let p = raw;
	if (base && (p === base || p.startsWith(`${base}/`))) p = p.slice(base.length) || '/';
	if (!p.startsWith('/') || p.startsWith('//') || p.startsWith('/\\')) return null;
	// eslint-disable-next-line no-control-regex
	if (/[\u0000-\u001f\u007f]/.test(p) || p.includes('://')) return null;
	return p;
}

/** 부모 경로 — 마지막 세그먼트를 떼고, 탭 루트('/today' 등) 아래에서는 그 루트. 루트 자체는 null. */
export function parentPath(path: string): string | null {
	const clean = path.split(/[?#]/)[0].replace(/\/+$/, '');
	const segs = clean.split('/').filter(Boolean);
	if (segs.length <= 1) return null;
	return `/${segs.slice(0, -1).join('/')}`;
}

/** 현재 경로 + ?from= → 돌아갈 경로(base 제외). from 이 유효하면 우선, 아니면 부모, 부모도 없으면 fallback. */
export function backTarget(currentPath: string, from: string | null | undefined, base = '', fallback = '/today'): string {
	return safeInternalPath(from, base) ?? parentPath(currentPath) ?? fallback;
}

/** 다른 화면으로 보낼 때 돌아올 자리를 달아 준다. 이미 쿼리가 있으면 &로 잇는다. */
export function withFrom(href: string, here: string): string {
	const safe = safeInternalPath(here);
	if (!safe) return href;
	return `${href}${href.includes('?') ? '&' : '?'}from=${encodeURIComponent(safe)}`;
}
