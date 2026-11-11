// P-25 — 로더가 기다리지 않고 넘긴 보조 데이터(약속)를 화면 상태로 옮긴다. 순수 모듈(Svelte 비의존).
//
// - 같은 화면(key 동일)에서 다시 읽기(invalidate)로 새 약속이 오면, 끝날 때까지 이전 값을 그대로 둔다(깜빡임 없음).
// - 다른 화면(key 변경, 예: 다른 플랜 id)으로 바뀌면 이전 값을 바로 지우고(undefined → 스켈레톤) 새 값을 기다린다.
// - 늦게 끝난 옛 약속이 새 값을 덮어쓰지 않도록 마지막 약속만 반영한다.
// 약속은 거부되지 않게 만들어 넘긴다(toResult·catch). 혹시 거부되면 undefined 로 둔다(스켈레톤 유지 대신 빈 자리).

export type StreamSetter<T> = (value: T | undefined, settled: boolean) => void;

export function createStreamFollower<T>(set: StreamSetter<T>): (key: string, p: Promise<T>) => void {
	let seq = 0;
	let lastKey: string | null = null;
	return (key, p) => {
		const n = ++seq;
		if (key !== lastKey) {
			lastKey = key;
			set(undefined, false);
		}
		p.then(
			(v) => {
				if (n === seq) set(v, true);
			},
			() => {
				if (n === seq) set(undefined, true);
			}
		);
	};
}
