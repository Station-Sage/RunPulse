// 오버레이 공통 동작의 순수 코어(DOM 비의존) — 스택·Tab 순환·스크롤 잠금 카운터. design overlay-common-behavior §2.1.

export const FOCUSABLE_SELECTOR =
	'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export interface OverlayStack {
	push(id: string): void;
	pop(id: string): void;
	top(): string | null;
	isTop(id: string): boolean;
	size(): number;
}

// 겹친 오버레이 중 Esc·트랩을 받을 대상(맨 위)을 하나로 정한다. 같은 id 를 다시 push 하면 맨 위로 옮긴다.
export function createOverlayStack(): OverlayStack {
	let ids: string[] = [];
	return {
		push(id) {
			ids = ids.filter((x) => x !== id);
			ids.push(id);
		},
		pop(id) {
			ids = ids.filter((x) => x !== id);
		},
		top: () => (ids.length ? ids[ids.length - 1] : null),
		isTop: (id) => ids.length > 0 && ids[ids.length - 1] === id,
		size: () => ids.length
	};
}

// Tab/Shift+Tab 순환 인덱스. current 가 범위 밖(-1: 포커스가 트랩 바깥)이면 방향에 따라 처음/끝으로 보낸다. count=0 이면 -1.
export function nextFocusIndex(count: number, current: number, shift: boolean): number {
	if (count <= 0) return -1;
	if (current < 0 || current >= count) return shift ? count - 1 : 0;
	return shift ? (current - 1 + count) % count : (current + 1) % count;
}

export interface ScrollLock {
	acquire(): void;
	release(): void;
	count(): number;
}

// 참조 카운터. 0→1 에서만 lock(), 1→0 에서만 unlock() 을 호출한다(OVL-6). 실제 style 적용은 호출자가 주입.
export function createScrollLock(lock: () => void, unlock: () => void): ScrollLock {
	let n = 0;
	return {
		acquire() {
			if (n++ === 0) lock();
		},
		release() {
			if (n === 0) return;
			if (--n === 0) unlock();
		},
		count: () => n
	};
}
