// "새 버전" 알림 — 오래된 탭 복구 (SEC-8 (b), security-headers.md §2.4, S3-10).
// 자동 새로고침은 입력 중 데이터를 잃게 하므로 하지 않는다. 알림을 띄우고 사용자가 누를 때만 새로고침한다.
// 순수 함수(shouldNotify·shouldCheck)는 DOM 없이 테스트한다. 스토어·DOM 연결은 hooks.client.ts 가 맡는다.

import { writable } from 'svelte/store';

export const NOTICE_STORAGE_KEY = 'runpulse.updateNoticeBuild';
/** 탭이 다시 보일 때 version.json 을 확인하는 최소 간격(ms). 폴링이 아니라 복귀 시점 1회 확인이다. */
export const CHECK_MIN_INTERVAL_MS = 5 * 60 * 1000;

type StorageLike = Pick<Storage, 'getItem' | 'setItem'>;

/** 알림 표시 여부. true 면 지금 표시한다. */
export const updateNoticeVisible = writable(false);

/**
 * 이 빌드(buildId)에서 알림을 아직 띄우지 않았으면 true 를 돌려주고 기록한다.
 * 같은 세션(sessionStorage)에서 같은 빌드로는 중복 표시하지 않는다. 저장소를 못 쓰면 true(알림 우선).
 */
export function shouldNotify(storage: StorageLike | null | undefined, buildId: string): boolean {
	if (!storage) return true;
	try {
		if (storage.getItem(NOTICE_STORAGE_KEY) === buildId) return false;
		storage.setItem(NOTICE_STORAGE_KEY, buildId);
	} catch {
		return true;
	}
	return true;
}

/** 탭 복귀 시 버전 확인을 해도 되는지. 마지막 확인이 없거나 최소 간격이 지났을 때만 true. */
export function shouldCheck(lastCheckMs: number | null, nowMs: number, minIntervalMs = CHECK_MIN_INTERVAL_MS): boolean {
	if (lastCheckMs === null) return true;
	return nowMs - lastCheckMs >= minIntervalMs;
}

/** 알림을 띄운다(이 빌드에서 처음일 때만). 이미 떠 있으면 그대로 둔다. */
export function notifyUpdate(storage: StorageLike | null | undefined, buildId: string): boolean {
	if (!shouldNotify(storage, buildId)) return false;
	updateNoticeVisible.set(true);
	return true;
}
