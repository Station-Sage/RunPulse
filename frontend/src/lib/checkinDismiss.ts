// B2 `✕ 나중에` — 오늘은 컨디션 입력 카드를 다시 올리지 않는다(날짜별 키, 브라우저 저장소).
// 저장소가 막혀 있어도(사생활 보호 모드 등) 화면은 그대로 동작해야 하므로 모든 접근을 try/catch로 감싼다.
export type KV = Pick<Storage, 'getItem' | 'setItem'>;

const PREFIX = 'rp:checkin-later:';

function defaultStore(): KV | null {
	try {
		return typeof localStorage === 'undefined' ? null : localStorage;
	} catch {
		return null;
	}
}

export function isDismissed(date: string, store: KV | null = defaultStore()): boolean {
	if (!store || !date) return false;
	try {
		return store.getItem(PREFIX + date) === '1';
	} catch {
		return false;
	}
}

export function dismiss(date: string, store: KV | null = defaultStore()): void {
	if (!store || !date) return;
	try {
		store.setItem(PREFIX + date, '1');
	} catch {
		/* 저장 실패는 무시 — 이번 세션 동안만 접힌다 */
	}
}
