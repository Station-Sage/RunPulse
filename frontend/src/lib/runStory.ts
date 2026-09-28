// frontend/src/lib/runStory.ts
// 활동 "한 줄 판정" — km 스플릿에서 전·후반 페이스, 심박 상승, 유산소 디커플링을 근거와 함께 도출한다.
// 모든 문장은 아래 fact(근거)로 뒷받침되어야 한다(P2 투명성). 테스트: frontend/tests/runStory.test.mjs
import type { Split } from './splits';

export type FactTone = 'good' | 'warn' | 'neutral';
export interface StoryFact {
	key: 'pace' | 'hr' | 'decoupling' | 'fastest';
	label: string;
	value: string;
	tone: FactTone;
	hint: string;
}
export interface RunStory {
	kind: 'negative' | 'positive' | 'even';
	headline: string;
	facts: StoryFact[];
}

function mmss(sec: number): string {
	const s = Math.round(Math.abs(sec));
	return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}
const mean = (v: number[]) => v.reduce((a, b) => a + b, 0) / v.length;

/** 완전한 1km 구간이 4개 미만이면 null. 전반/후반은 구간 수의 앞·뒤 절반(홀수면 가운데 제외). */
export function buildRunStory(splits: Split[], decouplingPct: number | null = null): RunStory | null {
	const full = splits.filter((s) => s.distanceM >= 1000);
	if (full.length < 4) return null;
	const half = Math.floor(full.length / 2);
	const first = full.slice(0, half);
	const second = full.slice(full.length - half);

	const p1 = mean(first.map((s) => s.paceSecKm));
	const p2 = mean(second.map((s) => s.paceSecKm));
	const diff = p2 - p1; // 음수 = 후반이 빠름
	const rel = diff / p1;
	const kind: RunStory['kind'] = rel <= -0.02 ? 'negative' : rel >= 0.02 ? 'positive' : 'even';

	const paces = full.map((s) => s.paceSecKm);
	const cv = Math.sqrt(mean(paces.map((p) => (p - mean(paces)) ** 2))) / mean(paces);

	let headline: string;
	if (kind === 'negative') headline = `후반이 전반보다 ${mmss(diff)}/km 빨랐어요 — 네거티브 스플릿`;
	else if (kind === 'positive') headline = `후반에 ${mmss(diff)}/km 느려졌어요 — 페이스가 떨어졌습니다`;
	else headline = `전 구간 페이스가 일정했어요 (편차 ±${(cv * 100).toFixed(1)}%)`;

	const facts: StoryFact[] = [
		{
			key: 'pace',
			label: '전반 → 후반 페이스',
			value: `${mmss(p1)} → ${mmss(p2)}`,
			tone: kind === 'positive' ? 'warn' : kind === 'negative' ? 'good' : 'neutral',
			hint: `앞 ${half}km 평균과 뒤 ${half}km 평균`
		}
	];

	const hr1 = first.map((s) => s.avgHr).filter((v): v is number => v != null);
	const hr2 = second.map((s) => s.avgHr).filter((v): v is number => v != null);
	if (hr1.length && hr2.length) {
		const h1 = mean(hr1);
		const h2 = mean(hr2);
		facts.push({
			key: 'hr',
			label: '전반 → 후반 심박',
			value: `${Math.round(h1)} → ${Math.round(h2)} bpm`,
			tone: 'neutral',
			hint: '구간 평균 심박(전·후반)'
		});
	}
	// 유산소 디커플링은 백엔드 aerobic_decoupling_rp 한 곳에서만 계산한다(Friel: 첫 10분 제외·이동 시간 절반, 재계산 금지)
	if (decouplingPct != null && Number.isFinite(decouplingPct)) {
		const dec = decouplingPct;
		facts.push({
			key: 'decoupling',
			label: '유산소 디커플링',
			value: `${dec >= 0 ? '' : '−'}${Math.abs(dec).toFixed(1)}%`,
			tone: Math.abs(dec) < 5 ? 'good' : Math.abs(dec) < 8 ? 'neutral' : 'warn',
			hint: '첫 10분을 뺀 이동 시간 전·후반의 심박당 속도 변화 — 5% 미만이면 유산소 안정'
		});
	}

	const fi = paces.indexOf(Math.min(...paces));
	facts.push({
		key: 'fastest',
		label: '가장 빠른 구간',
		value: `${full[fi].km}km · ${mmss(full[fi].paceSecKm)}`,
		tone: 'neutral',
		hint: `${full.length}개 구간 중 최고`
	});

	return { kind, headline, facts };
}
