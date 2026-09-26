<script lang="ts">
	// 대회 확인(P7-PRED-73): 대회로 보이는 활동에 전력/페이스/펀런/DNF 를 표시 — 예측은 '전력'만 기준으로 쓴다.
	import { onMount } from 'svelte';
	import type { RaceCandidate, RaceEffort } from '$lib/types';
	import { deleteRaceConfirm, getRaceCandidates, putRaceConfirm } from '$lib/api/prediction';
	import { formatDuration } from '$lib/format';

	const EFFORTS: { key: RaceEffort; label: string }[] = [
		{ key: 'allout', label: '전력' },
		{ key: 'paced', label: '페이스' },
		{ key: 'fun', label: '펀런' },
		{ key: 'dnf', label: 'DNF' }
	];

	let items = $state<RaceCandidate[]>([]);
	let loaded = $state(false);
	let busy = $state<number | null>(null);

	onMount(() => {
		getRaceCandidates()
			.then((r) => (items = r))
			.finally(() => (loaded = true));
	});

	async function choose(item: RaceCandidate, effort: RaceEffort) {
		busy = item.activity_id;
		try {
			if (item.confirmed_effort === effort) {
				await deleteRaceConfirm(item.activity_id);
				item.confirmed_effort = null;
			} else {
				await putRaceConfirm(item.activity_id, effort);
				item.confirmed_effort = effort;
			}
		} finally {
			busy = null;
		}
	}
</script>

<div class="flex flex-col gap-2" aria-label="대회 확인">
	<span class="text-xs text-fg-muted">대회 기록 확인 · 예측은 '전력'으로 표시한 대회만 기준으로 써요</span>
	{#if !loaded}
		<p class="text-[11px] text-fg-muted">불러오는 중…</p>
	{:else if items.length === 0}
		<p class="text-[11px] text-fg-muted">최근 1년 대회로 보이는 활동이 없어요</p>
	{:else}
		<ul class="flex flex-col gap-2">
			{#each items as item (item.activity_id)}
				<li class="flex flex-col gap-1">
					<span class="text-[11px]"
						>{item.date} · {item.name ?? '대회'} · {(item.distance_m / 1000).toFixed(1)}km{item.time_sec != null
							? ` · ${formatDuration(item.time_sec)}`
							: ''}</span
					>
					<div class="flex gap-1">
						{#each EFFORTS as e (e.key)}
							<button
								type="button"
								disabled={busy === item.activity_id}
								aria-pressed={item.confirmed_effort === e.key}
								onclick={() => choose(item, e.key)}
								class="rounded border px-2 py-0.5 text-[11px] {item.confirmed_effort === e.key
									? 'border-fg-primary text-fg-primary'
									: 'border-border-subtle text-fg-muted'}">{e.label}</button
							>
						{/each}
					</div>
				</li>
			{/each}
		</ul>
	{/if}
</div>
