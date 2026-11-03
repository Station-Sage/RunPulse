<script lang="ts">
	// 내보낼 데이터 그룹 선택 — 민감 그룹은 표시하고, 기록(episodes) 해제분 포함은 하위 선택으로 둔다.
	import { GROUP_HINTS, toggleKey, type ExportGroup } from '$lib/exportScope';

	let {
		groups,
		selected = $bindable(),
		includeDismissed = $bindable()
	}: { groups: ExportGroup[]; selected: string[]; includeDismissed: boolean } = $props();
</script>

<fieldset class="flex flex-col gap-1">
	<legend class="mb-1 text-xs font-semibold text-fg-primary">내보낼 데이터</legend>
	<div class="flex gap-2">
		<button type="button" class="tap text-xs underline" onclick={() => (selected = groups.map((g) => g.key))}>전체 선택</button>
		<button type="button" class="tap text-xs underline" onclick={() => (selected = [])}>전체 해제</button>
	</div>
	{#each groups as g (g.key)}
		<label class="tap flex items-start gap-3 rounded-lg border border-border-subtle bg-surface-2 p-3">
			<input
				type="checkbox"
				class="mt-0.5 size-5"
				checked={selected.includes(g.key)}
				onchange={() => (selected = toggleKey(selected, g.key))}
			/>
			<span class="flex flex-col">
				<span class="text-sm text-fg-primary">
					{g.label}{#if g.sensitive}<span class="ml-1 text-xs text-semantic-amber">민감 정보 포함</span>{/if}
				</span>
				<span class="text-xs text-fg-secondary">{GROUP_HINTS[g.key] ?? ''}</span>
			</span>
		</label>
		{#if g.key === 'episodes'}
			<label class="tap ml-8 flex items-center gap-3 text-xs text-fg-secondary">
				<input
					type="checkbox"
					class="size-5"
					bind:checked={includeDismissed}
					disabled={!selected.includes('episodes')}
				/>
				해제한 기록도 포함
			</label>
		{/if}
	{/each}
</fieldset>
