// 활동 상세 → 목록 뒤로가기 보조(A-39). 순수 함수 + sessionStorage 래퍼. 테스트: frontend/tests/activityListB2.test.mjs
const KEY = 'runpulse.activityListQuery';

type Store = Pick<Storage, 'getItem' | 'setItem'>;

function session(): Store | null {
	try {
		return typeof sessionStorage === 'undefined' ? null : sessionStorage;
	} catch {
		return null;
	}
}

/** 목록이 마지막으로 쓴 필터 쿼리('?a=b' 또는 '')를 탭 세션에 기억한다. */
export function rememberListQuery(qs: string, store: Store | null = session()): void {
	try {
		store?.setItem(KEY, qs.startsWith('?') || qs === '' ? qs : `?${qs}`);
	} catch {
		/* 저장소 접근 불가 — 필터 없는 목록으로 돌아간다 */
	}
}

/** 목록 경로에 기억한 필터를 붙인다. 목록이 아닌 목적지는 그대로. */
export function listBackPath(path: string, store: Store | null = session()): string {
	if (path !== '/library/activities') return path;
	let qs = '';
	try {
		qs = store?.getItem(KEY) ?? '';
	} catch {
		qs = '';
	}
	return /^\?[^#\s]*$/.test(qs) ? `${path}${qs}` : path;
}

/**
 * 활동 상세에서 history.back() 을 써도 되는지 — 앱 안에서 들어왔을 때만.
 * 같은 활동의 탭 이동(replaceState)은 판단을 바꾸지 않는다(예전에는 탭 이동 뒤 false 가 되어 필터 없는 목록으로 갔다).
 */
export function nextCameFromApp(prev: boolean, navType: string, fromPath: string | null, activityPath: string): boolean {
	if (navType === 'enter') return false;
	if (!fromPath) return prev;
	const same = fromPath === activityPath || fromPath.startsWith(`${activityPath}/`);
	return same ? prev : true;
}
