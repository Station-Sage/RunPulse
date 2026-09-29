// Today 히어로·게이지 순수 로직 — 문구 조립, 조사, 게이지 기하. 테스트: tests/todayHero.test.mjs
// 판정·등급은 서버(bands.py / readiness_decision)가 내려준 값만 쓴다. 여기서는 임계값을 두지 않는다.
import type { BriefingCaveat, BriefingStateFields } from './types/index';
import { formatDistance, formatPaceRange } from './format.ts';

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'];

function hasFinalConsonant(word: string): boolean {
	const code = word.charCodeAt(word.length - 1) - 0xac00;
	return code >= 0 && code <= 11171 && code % 28 !== 0;
}

/** 받침이 있으면 '을', 없으면 '를'. */
export function eulReul(word: string): string {
	return `${word}${hasFinalConsonant(word) ? '을' : '를'}`;
}

/** 받침 없음/ㄹ받침이면 '로', 그 외 받침이면 '으로'. */
export function euroRo(word: string): string {
	const code = word.charCodeAt(word.length - 1) - 0xac00;
	const final = code >= 0 && code <= 11171 ? code % 28 : 0;
	return `${word}${final === 0 || final === 8 ? '로' : '으로'}`;
}

/** "아침 기준 · 9월 27일 (일)" — 하루 한 번 아침 스냅샷임을 밝히는 B3 헤더 문구. */
export function morningAsOf(date: string): string {
	const [y, m, d] = date.split('-').map(Number);
	const dow = WEEKDAYS[new Date(Date.UTC(y, m - 1, d)).getUTCDay()];
	return `아침 기준 · ${m}월 ${d}일 (${dow})`;
}

export interface HeroView {
	headline: string;
	sub: string;
	adjustment: string | null;
	tone: 'neutral' | 'caution' | 'done';
	cta: 'plan_new' | 'session' | 'activity' | null;
}

function sessionSub(b: BriefingStateFields): string {
	const s = b.session;
	if (!s) return '';
	const parts: string[] = [];
	if (s.distance_m) parts.push(formatDistance(s.distance_m));
	const pace = formatPaceRange(s.pace_min, s.pace_max);
	if (pace) parts.push(pace);
	if (s.zone != null && s.zone !== '') parts.push(`Z${String(s.zone).replace(/^Z/i, '')}`);
	return parts.join(' · ');
}

/** briefing.state → 히어로 문구. 완료 비율은 신뢰 가능할 때만(서버가 null이면 생략). */
export function heroView(b: BriefingStateFields): HeroView {
	const adj = b.adjustment;
	const adjustment = adj ? `⚠ ${adj.reason ? `${adj.reason} → ` : ''}${eulReul(adj.from)} ${euroRo(adj.to)}` : null;
	const km = b.today_result ? formatDistance(b.today_result.distance_m) : '';
	switch (b.state) {
		case 'pre':
			return { headline: `오늘 · ${b.session?.title ?? '훈련'}`, sub: sessionSub(b), adjustment,
				tone: adj ? 'caution' : 'neutral', cta: b.session?.id != null ? 'session' : null };
		case 'done': {
			const ratio = b.today_result?.plan_ratio_pct;
			return { headline: `오늘 완료 ✓ ${km}`, sub: ratio != null ? `계획의 ${ratio}%` : '', adjustment: null,
				tone: 'done', cta: 'activity' };
		}
		case 'extra':
			return { headline: `오늘 ${km} 달렸어요`, sub: '', adjustment: null, tone: 'done', cta: 'activity' };
		case 'rest':
			return { headline: '오늘은 휴식', sub: '', adjustment: null, tone: 'neutral', cta: null };
		case 'race_week':
			return { headline: '레이스 주간이에요', sub: sessionSub(b), adjustment, tone: adj ? 'caution' : 'neutral',
				cta: b.session?.id != null ? 'session' : null };
		case 'race_day':
			return { headline: '오늘은 레이스 날이에요', sub: '', adjustment: null, tone: 'neutral', cta: null };
		default:
			return { headline: '아직 훈련 계획이 없어요', sub: '목표 레이스를 정하면 오늘 할 훈련을 알려드려요.',
				adjustment: null, tone: 'neutral', cta: 'plan_new' };
	}
}

/** 결손 caveat → 안내 문구(판정은 있는 데이터 기준임을 밝힘). */
export function caveatText(c: BriefingCaveat, providerName: (k: string) => string): string {
	if (c.code === 'source_missing') {
		const who = c.provider ? providerName(c.provider) : '일부 소스';
		return `${who} 데이터가 ${c.days ?? 1}일째 들어오지 않아 있는 데이터 기준으로 판단했어요.`;
	}
	return '일부 데이터가 없어 있는 데이터 기준으로 판단했어요.';
}

/** TSB 양방향 반원 바늘 각도(도). -40..+40 → 180..0 (음수 왼쪽). 범위 밖은 clamp. */
export function bipolarAngle(value: number, limit = 40): number {
	const v = Math.min(limit, Math.max(-limit, value));
	return 180 - ((v + limit) / (2 * limit)) * 180;
}

/** CIRS 3분할 트랙 마커 위치(0~100%). */
export function trackPct(value: number, min = 0, max = 100): number {
	if (!(max > min)) return 0;
	return Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100));
}

/** 전일 대비 표시: +3 / -2 / 0 / null이면 ''. */
export function deltaText(delta: number | null | undefined): string {
	if (delta == null) return '';
	if (delta === 0) return '±0';
	return `${delta > 0 ? '+' : '−'}${Math.abs(delta)}`;
}
