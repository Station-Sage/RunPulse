import { apiFetch } from './client';
import type { ActivityStreamsResponse } from '$lib/types';

/** `?max_points=` 로 줄였을 때만 붙는 원본(from)·응답(to) 점 수(A-36). 없으면 전체 해상도. */
export type DownsampledStreamsResponse = ActivityStreamsResponse & { downsampled?: { from: number; to: number } };

/** 스트림 탭 차트가 요청하는 최대 점 수(A-36) — Sparkline viewBox 폭(600)보다 넉넉히 커서 그린 선은 사실상 같다. */
export const STREAM_CHART_MAX_POINTS = 1000;

/** maxPoints 를 주면 서버가 균등 간격으로 줄여 보낸다(응답 `downsampled.from` = 원본 점 수). 없으면 전체 해상도. */
export function getActivityStreams(activityId: number, maxPoints?: number): Promise<DownsampledStreamsResponse> {
	const q = maxPoints != null ? `?max_points=${maxPoints}` : '';
	return apiFetch<DownsampledStreamsResponse>(`/library/activities/${activityId}/streams${q}`);
}
