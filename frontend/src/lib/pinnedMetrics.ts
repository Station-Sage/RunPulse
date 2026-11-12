// "내 지표" 고정 목록 — localStorage 저장(없으면 기본 세트). 저장 불가 환경은 메모리로만 동작.
const KEY = 'rp.library.pinned';
type Store = Pick<Storage, 'getItem' | 'setItem'>;

export const DEFAULT_PINS = [
	'race_pred_marathon_sec', 'race_pred_half_sec', 'race_pred_10k_sec', 'race_pred_5k_sec', 'ctl', 'tsb', 'utrs', 'cirs'
];

function safeStore(): Store | undefined {
	try {
		return typeof localStorage === 'undefined' ? undefined : localStorage;
	} catch {
		return undefined;
	}
}

export function loadPins(store: Store | undefined = safeStore()): string[] {
	try {
		const raw = store?.getItem(KEY);
		if (!raw) return [...DEFAULT_PINS];
		const v = JSON.parse(raw);
		return Array.isArray(v) && v.every((x) => typeof x === 'string') ? v : [...DEFAULT_PINS];
	} catch {
		return [...DEFAULT_PINS];
	}
}

export function savePins(pins: string[], store: Store | undefined = safeStore()) {
	try {
		store?.setItem(KEY, JSON.stringify(pins));
	} catch {
		/* 저장 불가는 무시 */
	}
}

export function togglePin(pins: string[], name: string): string[] {
	return pins.includes(name) ? pins.filter((p) => p !== name) : [...pins, name];
}

/** M-30: 고정 목록은 이 기기(브라우저)에만 저장한다 — 서버 동기화는 하지 않는다(S4-85, TXT-1 확정). */
export const PINS_DEVICE_NOTE = '이 기기에만 저장';
