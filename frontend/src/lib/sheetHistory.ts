// OVL-4 URL 연동 시트 — 열 때 pushState(`?sheet=name`), 닫을 때 앱에서 연 건 뒤로가기, 딥링크는 goto(replaceState) — shallow replaceState 는 page.url 을 갱신하지 않는다.
// pushState 는 page.url 을 갱신하지 않으므로 열림 판정은 sheetOpen 으로 한다(state 우선, 아니면 URL).
import { goto, pushState } from '$app/navigation';
import { page } from '$app/state';

export function sheetOpen(name: string): boolean {
	return page.state.sheet === name || page.url.searchParams.get('sheet') === name;
}

export function openSheet(name: string) {
	if (sheetOpen(name)) return;
	const u = new URL(page.url);
	u.searchParams.set('sheet', name);
	pushState(u, { sheet: name });
}

export function closeSheet(name: string) {
	if (!sheetOpen(name)) return;
	if (page.state.sheet === name) {
		history.back();
		return;
	}
	const u = new URL(page.url);
	u.searchParams.delete('sheet');
	void goto(u, { replaceState: true, keepFocus: true, noScroll: true });
}
