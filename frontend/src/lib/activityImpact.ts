// '이 러닝의 의미' 표시 — 문장은 서버가 만든다(규칙 줄 lines + AI 요약 wording, ADR-059). 여기서는 고르기만 한다.
import { isAiWorded } from './aiWording.ts';

export interface ImpactWordingLite {
	lines?: string[] | null;
	wording?: { text: string; source: 'ai' | 'rule' } | null;
}

export interface ImpactView {
	lines: string[];
	/** AI 요약(source==='ai')일 때만 문장, 아니면 null — 규칙 줄은 그대로 보인다. */
	ai: string | null;
}

export function impactView(i: ImpactWordingLite | null | undefined): ImpactView {
	const lines = i?.lines ?? [];
	const ai = isAiWorded(i?.wording) && i?.wording?.text ? i.wording.text : null;
	return { lines, ai };
}
