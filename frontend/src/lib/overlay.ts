// 오버레이 공통 동작 action (OVL-2~3·5·6, patterns/overlay-common-behavior.md §2.2·2.3).
// 순수 계산은 overlayCore.ts, 여기는 DOM 연결만 한다. 배경 비활성은 포커스 트랩 + aria-modal 만 쓴다(inert·포털 없음).
import {
	FOCUSABLE_SELECTOR,
	createOverlayStack,
	createScrollLock,
	nextFocusIndex
} from './overlayCore';

export interface ModalOptions {
	onClose: () => void;
	initialFocus?: string;
	enabled?: boolean;
}

const stack = createOverlayStack();
let seq = 0;
let prevOverflow = '';
const scroll = createScrollLock(
	() => {
		prevOverflow = document.body.style.overflow;
		document.body.style.overflow = 'hidden';
	},
	() => {
		document.body.style.overflow = prevOverflow;
	}
);
const handlers = new Map<string, (e: KeyboardEvent) => void>();

function focusables(root: HTMLElement): HTMLElement[] {
	return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
		(el) => el.getAttribute('tabindex') !== '-1' && !el.closest('[hidden]')
	);
}

function onKeydown(e: KeyboardEvent) {
	const top = stack.top();
	const h = top ? handlers.get(top) : undefined;
	if (h) h(e);
}

function register(id: string, h: (e: KeyboardEvent) => void) {
	if (handlers.size === 0) document.addEventListener('keydown', onKeydown);
	handlers.set(id, h);
}

function unregister(id: string) {
	handlers.delete(id);
	if (handlers.size === 0) document.removeEventListener('keydown', onKeydown);
}

function restoreFocus(opener: HTMLElement | null) {
	if (stack.size() > 0) return;
	if (opener && opener.isConnected) opener.focus();
	else document.querySelector<HTMLElement>('main')?.focus?.();
}

export function modal(node: HTMLElement, opts: ModalOptions) {
	let cur = opts;
	let active = false;
	let id = '';
	let opener: HTMLElement | null = null;

	function start() {
		id = `modal-${++seq}`;
		opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
		stack.push(id);
		scroll.acquire();
		register(id, (e) => {
			if (e.key === 'Escape') {
				if (e.defaultPrevented) return;
				e.preventDefault();
				cur.onClose();
			} else if (e.key === 'Tab') {
				const list = focusables(node);
				if (list.length === 0) {
					e.preventDefault();
					node.focus();
					return;
				}
				const at = list.indexOf(document.activeElement as HTMLElement);
				const next = nextFocusIndex(list.length, at, e.shiftKey);
				const inside = at >= 0;
				const wrap = e.shiftKey ? at === 0 : at === list.length - 1;
				if (!inside || wrap) {
					e.preventDefault();
					list[next].focus();
				}
			}
		});
		if (!node.hasAttribute('tabindex')) node.setAttribute('tabindex', '-1');
		const target =
			(cur.initialFocus && node.querySelector<HTMLElement>(cur.initialFocus)) ||
			node.querySelector<HTMLElement>('[data-autofocus]') ||
			focusables(node)[0] ||
			node;
		target.focus();
		active = true;
	}

	function stop() {
		if (!active) return;
		active = false;
		unregister(id);
		stack.pop(id);
		scroll.release();
		restoreFocus(opener);
	}

	if (cur.enabled !== false) start();
	return {
		update(next: ModalOptions) {
			cur = next;
			if (next.enabled === false) stop();
			else if (!active) start();
		},
		destroy: stop
	};
}

export interface InlineConfirmOptions {
	onCancel: () => void;
}

// 인라인 확인 블록 — 트랩·잠금 없음. 열릴 때 [data-autofocus](없으면 첫 요소)로 포커스, Esc 는 취소, 닫히면 호출 버튼으로 복귀.
export function inlineConfirm(node: HTMLElement, opts: InlineConfirmOptions) {
	let cur = opts;
	const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
	(node.querySelector<HTMLElement>('[data-autofocus]') ?? focusables(node)[0])?.focus();
	function onKey(e: KeyboardEvent) {
		if (e.key !== 'Escape' || e.defaultPrevented) return;
		e.preventDefault();
		e.stopPropagation();
		cur.onCancel();
	}
	node.addEventListener('keydown', onKey);
	return {
		update(next: InlineConfirmOptions) {
			cur = next;
		},
		destroy() {
			node.removeEventListener('keydown', onKey);
			if (opener && opener.isConnected) opener.focus();
		}
	};
}
