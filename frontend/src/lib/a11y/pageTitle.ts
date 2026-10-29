// 문서 제목 조립 — 빈 부분을 버리고 "A · B · RunPulse" 로 잇는다.
export const APP_NAME = 'RunPulse';

export function pageTitle(...parts: Array<string | null | undefined>): string {
	const kept = parts.map((p) => (p ?? '').trim()).filter(Boolean);
	return [...kept, APP_NAME].join(' · ');
}
