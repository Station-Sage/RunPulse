// R3 — 화면에 보이는 조건부 문구를 낭독 공지로도 보내는 액션. 요소엔 role 을 달지 않는다.
import { announce, type Politeness } from './announce.ts';

export interface SayParam {
	text: string | null | undefined;
	level?: Politeness;
}

export function say(_node: unknown, p: SayParam) {
	announce(p.text, p.level);
	return {
		update(next: SayParam) {
			if (next.text !== p.text) announce(next.text, next.level);
			p = next;
		}
	};
}
