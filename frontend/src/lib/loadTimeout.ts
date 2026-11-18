// 부가 로더가 느려도 화면 전환이 막히지 않도록 시간 제한을 둔다 — 초과·실패 시 null.
export function softLoad<T>(p: Promise<T>, ms = 2500): Promise<T | null> {
	return new Promise((resolve) => {
		const t = setTimeout(() => resolve(null), ms);
		p.then(
			(v) => {
				clearTimeout(t);
				resolve(v);
			},
			() => {
				clearTimeout(t);
				resolve(null);
			}
		);
	});
}
