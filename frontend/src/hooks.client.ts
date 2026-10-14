// 클라이언트 훅 — 오래된 탭 복구 (SEC-8 (b), D8). 자동 새로고침 없이 "새 버전" 알림만 띄운다.
//
// 트리거 2가지:
//  1) `vite:preloadError` — 새 배포로 청크 파일이 사라져 동적 import 가 실패했을 때. 기본 동작(오류 throw)을 막고 알림.
//  2) 탭 복귀(visibilitychange) 시 SvelteKit `updated.check()` — `_app/version.json` 1건 확인(최소 5분 간격).
//     pollInterval 은 기존값(0)을 유지한다(SEC-11). 확인은 폴링이 아니라 탭이 다시 보일 때만 한다.
// 참고: SvelteKit 은 **내비게이션 중** 로드 실패 시 새 버전이면 스스로 전체 페이지 이동(native navigation)한다 —
// 사용자가 이미 다른 화면으로 이동하려던 중이라 입력 유실 위험이 없고, 이 동작은 끌 수 없다.
import { browser, version } from '$app/environment';
import { updated } from '$app/state';
import { notifyUpdate, shouldCheck } from '$lib/updateNotice';

function session(): Storage | null {
	try {
		return window.sessionStorage;
	} catch {
		return null;
	}
}

if (browser) {
	window.addEventListener('vite:preloadError', (event) => {
		event.preventDefault();
		notifyUpdate(session(), version);
	});

	let lastCheck: number | null = null;
	document.addEventListener('visibilitychange', async () => {
		if (document.visibilityState !== 'visible') return;
		const now = Date.now();
		if (!shouldCheck(lastCheck, now)) return;
		lastCheck = now;
		if (await updated.check()) notifyUpdate(session(), version);
	});
}
