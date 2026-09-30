import type { CoachChip } from './types';

/** 자유 입력(문자열) 또는 서버 질문 칩 — 칩은 chip_id 로 보내 규칙 핸들러가 답한다. */
export type CoachInput = string | CoachChip;

export function messageBody(input: CoachInput, textKey: 'content' | 'initial_message'): Record<string, string> {
	return typeof input === 'string' ? { [textKey]: input } : { chip_id: input.chip_id };
}

/** 낙관적 사용자 말풍선에 보일 문장. */
export function inputText(input: CoachInput): string {
	return typeof input === 'string' ? input : input.text;
}
