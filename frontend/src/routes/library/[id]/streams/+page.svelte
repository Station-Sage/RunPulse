<script lang="ts">
	// 03c-library.md 3-D — 활동 스트림 시각화 페이지.
	// 체크박스로 표시할 스트림 토글; 해당 컬럼이 전부 null이면 체크박스 숨김.
	import type { StreamsPageData } from './+page';
	import ActivityTabs from '$lib/components/ActivityTabs.svelte';
	import Sparkline from '$lib/components/Sparkline.svelte';
	import { base } from '$app/paths';
	import type { ActivityStreamPoint } from '$lib/types';
	import { indexAtFraction, axisTicks, formatElapsed } from '$lib/streamAxis';

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

	// 표시 토글 상태 (key → boolean) — 3-D 목업 기본값: 페이스·심박·고도 표시, 케이던스·파워 숨김.
	// 초기값을 선언 시점에 채운다: bind:checked가 마운트 때 undefined를 false로 덮어써서, 예전처럼
	// $effect로 나중에 true를 채우는 방식은 항상 져서 차트가 하나도 안 그려졌다(합성 데이터 스모크에서 발견).
	let checked = $state<Record<string, boolean>>(
		Object.fromEntries(STREAM_DEFS.map((d) => [d.key, ['pace', 'heart_rate', 'altitude_m'].includes(d.key)]))
	);

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

	// 시간 눈금 (elapsed_sec 기준, 포인트 인덱스 등간격 위치에 실제 시간 라벨)
	const ticks = $derived(axisTicks(data.streams.map((p) => p.elapsed_sec)));

	// 스크럽 상태: scrubFrac(0~1) → scrubIndex
	let scrubFrac = $state<number | null>(null);
	const scrubIndex = $derived(
		scrubFrac != null ? indexAtFraction(data.streams.length, scrubFrac) : null
	);

	function onPointerMove(e: PointerEvent) {
		const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
		scrubFrac = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
	}

	function onPointerLeave() {
		scrubFrac = null;
	}

	// 스크럽 판독 줄에 표시할 값 포맷
	function formatScrubValue(def: StreamDef, point: ActivityStreamPoint): string {
		const v = def.extract(point);
		if (v == null) return '—';
		if (def.key === 'pace') return formatPaceSec(v) + def.unit;
		return v.toFixed(0) + '\u00a0' + def.unit;
	}
</script>

<svelte:head><title>스트림 · RunPulse</title></svelte:head>

<!-- 헤더 -->
<div class="flex items-center gap-2 border-b border-border-subtle px-4 py-3">
	<a href="{base}/library/{data.activityId}" class="shrink-0 text-fg-muted" aria-label="활동 상세로">←</a>
	<h1 class="text-base font-semibold">스트림</h1>
</div>

<!-- 탭 -->
<ActivityTabs activityId={data.activityId} active="streams" />

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

		<!-- 시간 눈금 + 스크럽 영역 -->
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<div
			role="group"
			aria-label="스트림 차트 스크럽 영역"
			style="touch-action: pan-y"
			onpointerdown={onPointerMove}
			onpointermove={onPointerMove}
			onpointerleave={onPointerLeave}
			onpointercancel={onPointerLeave}
		>
			<!-- 시간 눈금: 포인트 인덱스 등간격 위치에 실제 elapsed_sec 라벨 -->
			<div class="relative mb-1 h-5 select-none">
				{#each ticks as tick}
					<span
						class="absolute -translate-x-1/2 text-xs text-fg-muted"
						style="left:{tick.frac * 100}%"
					>{tick.label}</span>
				{/each}
			</div>

			<!-- 판독 줄 (높이 고정 — 스크럽 여부와 무관하게 레이아웃 유지) -->
			<div class="mb-2 flex h-5 items-center gap-3 overflow-hidden text-xs">
				{#if scrubIndex != null}
					{@const point = data.streams[scrubIndex]}
					<span class="text-fg-muted">{formatElapsed(point.elapsed_sec)}</span>
					{#each availableStreams as def}
						{#if checked[def.key]}
							<span style="color:{def.color}">{def.label} {formatScrubValue(def, point)}</span>
						{/if}
					{/each}
				{/if}
			</div>

			<!-- 스트림 차트 목록 -->
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
							<!-- 스파크라인 + 스크럽 커서 라인 -->
							<div class="relative">
								<Sparkline data={values} height={48} color={def.color} />
								{#if scrubFrac != null}
									<div
										class="pointer-events-none absolute inset-y-0 w-px opacity-50"
										style="left:{scrubFrac * 100}%; background-color:{def.color}"
									></div>
								{/if}
							</div>
						</div>
					{/if}
				{/each}
			</div>
		</div>

		<p class="text-xs text-fg-muted">
			{data.streams.length.toLocaleString('ko-KR')}개 포인트 ·
			시간 눈금은 포인트 인덱스 기준 위치에 실제 elapsed_sec를 표시
		</p>
	</div>
{/if}
