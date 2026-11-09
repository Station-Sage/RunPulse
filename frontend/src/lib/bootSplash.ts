// S-05 — app.html 의 정적 로딩 화면(#rp-boot) 제거. 첫 화면(레이아웃 또는 오류 화면)이 그려진 뒤 호출한다.
export const BOOT_SPLASH_ID = 'rp-boot';

export function removeBootSplash(doc: Pick<Document, 'getElementById'> | undefined): boolean {
	const el = doc?.getElementById(BOOT_SPLASH_ID);
	if (!el) return false;
	el.remove();
	return true;
}
