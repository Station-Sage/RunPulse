// 생애주기 판정 — DESIGN-P7-REVIEW03 §2.0. Today 빈 분기가 "연결 안 됨"과 "첫 동기화 중"을 구분하는 단일 규칙.
import type { SyncState } from './syncState';

export type Lifecycle = 'syncing' | 'unconnected' | 'connected';

export function lifecycleOf(s: SyncState | null): Lifecycle {
	if (!s || s.connected_count === 0) return 'unconnected';
	return s.first_sync_running ? 'syncing' : 'connected';
}

export interface EmptyCopy {
	title: string;
	description: string;
	actionLabel: string;
	href: string;
}

// 막다른 링크 방지: 모든 분기는 v2에 실제 있는 라우트로 간다.
export function todayEmptyCopy(l: Lifecycle): EmptyCopy {
	if (l === 'syncing')
		return {
			title: '지난 기록을 가져오는 중이에요',
			description: '도착하는 대로 화면이 채워집니다. 기다리는 동안 목표 대회를 정해두세요.',
			actionLabel: '목표 대회 정하기',
			href: '/coach/plan/new'
		};
	if (l === 'connected')
		return {
			title: '아직 분석할 기록이 없어요',
			description: '연결은 되어 있어요. 달리기 기록이 들어오면 오늘 상태 분석이 시작됩니다.',
			actionLabel: '동기화 상태 보기',
			href: '/data/sync'
		};
	return {
		title: '기록 없이도 시작할 수 있어요',
		description: 'Garmin, Strava 등 소스를 연결하면 오늘 상태 분석이 시작됩니다. 컨디션 체크인은 지금도 가능해요.',
		actionLabel: '기기 연결하기',
		href: '/data/sources'
	};
}
