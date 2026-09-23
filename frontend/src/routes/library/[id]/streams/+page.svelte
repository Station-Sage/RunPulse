<script lang="ts">
	// 03c-library.md 3-D — 활동 스트림 시각화 페이지.
	// 체크박스로 표시할 스트림 토글; 해당 컬럼이 전부 null이면 체크박스 숨김.
	import type { StreamsPageData } from './+page';
	import Sparkline from '$lib/components/Sparkline.svelte';
	import { base } from '$app/paths';
	import type { ActivityStreamPoint } from '$lib/types';

	let { data }: { data: StreamsPageData } = $props();

	// pace_sec_km = speed_ms > 0 ? 1000/speed_ms : null
	function toPace(v: number | null): number | null {
		return v != null && v > 0 ? 1000 / v : null;
	}

	// 스트림 메타 정의: key, 라벨, 색상, 데이터 추출 함수
	type StreamDef = {
		key: string;
		label: string;
		color: string;
		extract: (p: ActivityStreamPoint) => number | null;
		unit: string;
	};

	const STREAM_DEFS: StreamDef[] = [
		{ key: 'pace', label: '페이스', color: '#3b82f6', extract: (p) => toPace(p.speed_ms), unit: '/km' },
		{ key: 'heart_rate', label: '심박수', color: '#ef4444', extract: (p) => p.heart_rate, unit: 'bpm' },
		{ key: 'altitude_m', label: '고도', color: '#10b981', extract: (p) => p.altitude_m, unit: 'm' },
		{ key: 'cadence', label: '케이던스', color: '#f59e0b', extract: (p) => p.cadence, unit: 'spm' },
		{ key: 'power_watts', label: '파워', color: '#8b5cf6', extract: (p) => p.power_watts, unit: 'W' }
	];

	// 전부 null인 스트림은 숨김
	const availableStreams = $derived(
		STREAM_DEFS.filter((def) => data.streams.some((p) => def.extract(p) != null))
	);

	// 표시 토글 상태 (key → boolean)
	let checked = $state<Record<string, boolean>>({});

	// 초기화: availableStreams가 바뀔 때 새로 생긴 키는 true로 설정
	$effect(() => {
		for (const def of availableStreams) {
			if (!(def.key in checked)) {
				checked[def.key] = true;
			}
		}
	});

	// provider 배지 (단일 source 또는 복합)
	const providerLabel = $derived((): string => {
		if (data.streams.length === 0) return '';
		const sources = [...new Set(data.streams.map((p) => p.source))];
		return sources.join(' / ');
	});

	function formatMinMax(vals: (number | null)[]): string {
		const nums = vals.filter((v): v is number => v != null);
		if (nums.length === 0) return '—';
		const mn = Math.min(...nums);
		const mx = Math.max(...nums);
		return `${mn.toFixed(1)} – ${mx.toFixed(1)}`;
	}

	function formatPaceSec(sec: number): string {
		const m = Math.floor(sec / 60);
		const s = Math.round(sec % 60);
		return `${m}:${String(s).padStart(2, '0')}`;
	}

	function formatMinMaxPace(vals: (number | null)[]): string {
		const nums = vals.filter((v): v is number => v != null);
		if (nums.length === 0) return '—';
		const mn = Math.min(...nums);
		const mx = Math.max(...nums);
		// 빠른 페이스가 min(낮은 값) → 빠른 페이스 먼저 표시
		return `${formatPaceSec(mn)} – ${formatPaceSec(mx)}`;
	}
</script>

<!-- 헤더 -->
<div class="flex items-center gap-2 border-b border-border-subtle px-4 py-3">
	<a href="{base}/library/{data.activityId}" class="shrink-0 text-fg-muted" aria-label="활동 상세로">←</a>
	<h1 class="text-base font-semibold">스트림</h1>
</div>

<!-- 탭 표시 (스트림 탭만 활성) -->
<div class="flex border-b border-border-subtle">
	<a href="{base}/library/{data.activityId}" class="flex-1 py-2.5 text-center text-sm text-fg-muted">요약</a>
	<a href="{base}/library/{data.activityId}/providers" class="flex-1 py-2.5 text-center text-sm text-fg-muted">소스 비교</a>
	<span class="flex-1 border-b-2 border-fg-primary py-2.5 text-center text-sm font-medium text-fg-primary">
		스트림
	</span>
</div>

<!-- 본문 -->
{#if data.errorMessage && data.streams.length === 0}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-secondary">{data.errorMessage}</p>
		<a href="{base}/library/{data.activityId}" class="mt-2 block text-xs text-fg-muted underline">← 활동으로 돌아가기</a>
	</div>
{:else if data.streams.length === 0}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-muted">스트림 데이터 없음</p>
		<a href="{base}/library/{data.activityId}" class="mt-2 block text-xs text-fg-muted underline">← 활동으로 돌아가기</a>
	</div>
{:else}
	<div class="flex flex-col gap-4 px-4 py-4">

		<!-- 토글 체크박스 -->
		<div class="flex flex-wrap gap-3">
			{#each availableStreams as def}
				<label class="flex cursor-pointer items-center gap-1.5 text-sm">
					<input
						type="checkbox"
						bind:checked={checked[def.key]}
						class="h-3.5 w-3.5 rounded"
					/>
					<span style="color:{def.color}">{def.label}</span>
				</label>
			{/each}
		</div>

		<!-- provider 배지 -->
		{#if providerLabel()}
			<p class="text-xs text-fg-muted">소스: {providerLabel()}</p>
		{/if}

		<!-- 스트림 목록 -->
		<div class="flex flex-col gap-5">
			{#each availableStreams as def}
				{#if checked[def.key]}
					{@const values = data.streams.map(def.extract)}
					<div class="flex flex-col gap-1">
						<div class="flex items-center justify-between text-xs text-fg-secondary">
							<span class="font-medium" style="color:{def.color}">{def.label}</span>
							<span class="text-fg-muted">
								{def.key === 'pace' ? formatMinMaxPace(values) : formatMinMax(values)}
								{def.unit}
							</span>
						</div>
						<Sparkline data={values} height={48} color={def.color} />
					</div>
				{/if}
			{/each}
		</div>

		<p class="text-xs text-fg-muted">
			{data.streams.length.toLocaleString('ko-KR')}개 포인트 ·
			x축은 포인트 순서(elapsed_sec 균등 간격 미보장 — 정밀 시간축은 후속 과제)
		</p>
	</div>
{/if}
