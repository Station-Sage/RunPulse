// E-17 — 온라인/오프라인 감시(순수 모듈, DOM 비의존: EventTarget 과 상태 조회 함수를 주입받는다).
import { OFFLINE_MESSAGES } from './utils/constants.ts';

export type ConnectivityPhase = 'online' | 'offline' | 'restored';

/** 배너 문구 — online(평상시)은 표시하지 않는다(null). */
export function connectivityText(phase: ConnectivityPhase): string | null {
	if (phase === 'offline') return OFFLINE_MESSAGES.offline;
	if (phase === 'restored') return OFFLINE_MESSAGES.restored;
	return null;
}

/**
 * online/offline 이벤트를 구독해 단계를 알린다. 오프라인에서 돌아오면 'restored' 를 보낸 뒤
 * `restoredMs` 후 'online' 으로 돌아간다. 반환값은 구독 해제 함수.
 */
export function watchConnectivity(
	target: EventTarget,
	isOnline: () => boolean,
	onPhase: (phase: ConnectivityPhase) => void,
	restoredMs = 3000
): () => void {
	let timer: ReturnType<typeof setTimeout> | undefined;
	const offline = () => {
		clearTimeout(timer);
		onPhase('offline');
	};
	const online = () => {
		clearTimeout(timer);
		onPhase('restored');
		timer = setTimeout(() => onPhase('online'), restoredMs);
	};
	target.addEventListener('offline', offline);
	target.addEventListener('online', online);
	if (!isOnline()) onPhase('offline');
	return () => {
		clearTimeout(timer);
		target.removeEventListener('offline', offline);
		target.removeEventListener('online', online);
	};
}
