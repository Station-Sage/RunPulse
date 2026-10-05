// 특수 드릴 시트 레지스트리 — `x.{id}` 토큰의 제목. 등록되지 않은 토큰은 폴백 문구로 안내한다.
export const TAPER_TOKEN = 'x.taper';

const SPECIAL: Record<string, string> = {
	[TAPER_TOKEN]: '레이스 아침 폼'
};

export function specialTitle(token: string): string | null {
	return SPECIAL[token] ?? null;
}

export const UNSUPPORTED_SPECIAL = '지원하지 않는 항목이에요';
