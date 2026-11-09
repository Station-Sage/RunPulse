<script lang="ts">
	import { say } from '$lib/a11y/say';
	// 대회 확인(P7-PRED-73): 대회로 보이는 활동에 전력/페이스/펀런/DNF 를 표시 — 예측은 '전력'만 기준으로 쓴다.
	import { onMount } from 'svelte';
	import type { RaceCandidate, RaceEffort } from '$lib/types';
	import { deleteRaceConfirm, getRaceCandidates, putRaceConfirm } from '$lib/api/prediction';
	import { formatDuration } from '$lib/format';
	import { candidateHint, nextEffort } from '$lib/raceConfirm';

	const EFFORTS: { key: RaceEffort; label: string }[] = [
		{ key: 'allout', label: '전력' },
		{ key: 'paced', label: '페이스' },
		{ key: 'fun', label: '펀런' },
		{ key: 'dnf', label: 'DNF' }
	];

	// onChanged: 저장 성공 뒤 호출 — 되돌리기 함수를 함께 넘긴다(예측 변화 토스트·undo는 부모가 담당).
	let { onChanged }: { onChanged?: (undo: () => Promise<void>) => void } = $props();

	let items = $state<RaceCandidate[]>([]);
	let loaded = $state(false);
	// 행별 진행 중 표시(T-13) — 한 행 저장이 다른 행의 보호를 풀지 않게 집합으로 둔다.
	let busy = $state<Set<number>>(new Set());
	let loadError = $state(false);
	let saveError = $state<string | null>(null);

	function load() {
		loadError = false;
		loaded = false;
		getRaceCandidates()
			.then((r) => (items = r))
			.catch(() => (loadError = true))
			.finally(() => (loaded = true));
	}
	onMount(load);

	async function apply(item: RaceCandidate, effort: RaceEffort | null) {
		if (effort === null) await deleteRaceConfirm(item.activity_id);
		else await putRaceConfirm(item.activity_id, effort);
		item.confirmed_effort = effort;
	}

	async function choose(item: RaceCandidate, effort: RaceEffort | null) {
		if (busy.has(item.activity_id)) return; // 빠른 연타 무시
		const prev = item.confirmed_effort ?? null;
		const next = nextEffort(prev, effort);
		if (next === undefined) return; // 같은 버튼 재탭 = 그대로(해제는 '표시 해제'로만)
		busy = new Set(busy).add(item.activity_id);
		saveError = null;
		try {
			await apply(item, next);
			onChanged?.(() => apply(item, prev));
		} catch (e) {
			saveError = e instanceof Error ? e.message : '저장하지 못했어요';
		} finally {
			const b = new Set(busy);
			b.delete(item.activity_id);
			busy = b;
		}
	}
</script>

<div class="flex flex-col gap-2" aria-label="대회 확인">
	<span class="text-xs text-fg-muted">대회 기록 확인 · 예측은 '전력'으로 표시한 대회만 기준으로 써요</span>
	{#if saveError}
		<p class="text-[11px] text-semantic-red" use:say={{ text: `저장하지 못했어요 · 다시 시도해 주세요 (${saveError})`, level: 'assertive' }}>저장하지 못했어요 · 다시 시도해 주세요 ({saveError})</p>
	{/if}
	{#if !loaded}
		<p class="text-[11px] text-fg-muted">불러오는 중…</p>
	{:else if loadError}
		<p class="text-[11px] text-fg-secondary" use:say={{ text: '대회 목록을 불러오지 못했어요', level: 'assertive' }}>
			대회 목록을 불러오지 못했어요 ·
			<button type="button" class="underline underline-offset-2" onclick={load}>다시 시도</button>
		</p>
	{:else if items.length === 0}
		<p class="text-[11px] text-fg-muted">최근 1년 대회로 보이는 활동이 없어요</p>
	{:else}
		<ul class="flex flex-col gap-2">
			{#each items as item (item.activity_id)}
				{@const hint = candidateHint(item)}
				{@const chosen = EFFORTS.find((e) => e.key === item.confirmed_effort)?.label ?? null}
				<li class="flex flex-col gap-1">
					<span class="text-[11px] break-words"
						>{item.date} · {item.name ?? '대회'} · {(item.distance_m / 1000).toFixed(1)}km{item.time_sec != null
							? ` · ${formatDuration(item.time_sec)}`
							: ''}</span
					>
					{#if hint}<span class="text-[11px] text-semantic-amber">{hint}</span>{/if}
					<div class="flex flex-wrap items-center gap-1">
						{#each EFFORTS as e (e.key)}
							<button
								type="button"
								disabled={busy.has(item.activity_id)}
								aria-pressed={item.confirmed_effort === e.key}
								onclick={() => choose(item, e.key)}
								class="rounded border px-2 py-0.5 text-[11px] {item.confirmed_effort === e.key
									? 'border-fg-primary font-semibold text-fg-primary'
									: 'border-border-subtle text-fg-muted'}">{#if item.confirmed_effort === e.key}<span aria-hidden="true">✓ </span>{/if}{e.label}</button
							>
						{/each}
						<!-- T-14: 선택 상태를 글로도 보인다. T-13: 해제는 별도 버튼으로만. -->
						<span class="text-[11px] text-fg-muted">{chosen ? `표시: ${chosen}` : '미표시'}</span>
						{#if chosen}
							<button type="button" disabled={busy.has(item.activity_id)} onclick={() => choose(item, null)} class="text-[11px] text-fg-muted underline underline-offset-2 hover:text-fg-primary">표시 해제</button>
						{/if}
					</div>
				</li>
			{/each}
		</ul>
	{/if}
</div>
