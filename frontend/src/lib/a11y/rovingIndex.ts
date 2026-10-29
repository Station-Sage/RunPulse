// 라디오그룹 화살표 키 이동 — 비활성 항목을 건너뛰고 양끝에서 순환한다.
export function nextIndex(current: number, key: string, count: number, disabled: boolean[] = []): number {
	if (count <= 0) return -1;
	const ok = (i: number) => !disabled[i];
	const step = (from: number, dir: 1 | -1): number => {
		for (let n = 1; n <= count; n++) {
			const i = (((from + dir * n) % count) + count) % count;
			if (ok(i)) return i;
		}
		return current;
	};
	switch (key) {
		case 'ArrowRight':
		case 'ArrowDown':
			return step(current, 1);
		case 'ArrowLeft':
		case 'ArrowUp':
			return step(current, -1);
		case 'Home':
			return ok(0) ? 0 : step(0, 1);
		case 'End':
			return ok(count - 1) ? count - 1 : step(count - 1, -1);
		default:
			return current;
	}
}
