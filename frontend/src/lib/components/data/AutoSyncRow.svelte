<script lang="ts">
	import { patchAutoSync, type AutoSyncSettings } from '$lib/api/data';

	let { settings }: { settings: AutoSyncSettings } = $props();
	let override = $state<AutoSyncSettings | null>(null);
	let busy = $state(false);
	let error = $state<string | null>(null);
	const cur = $derived(override ?? settings);
	const INTERVALS = [1, 2, 4, 6, 12, 24];
	const WINDOWS = [2, 7, 14, 30];

	const hm = (iso: string | null) => (iso ? iso.slice(11, 16) : null);

	async function change(body: Parameters<typeof patchAutoSync>[0]) {
		if (busy) return;
		busy = true;
		error = null;
		try {
			override = await patchAutoSync(body);
		} catch {
			error = '저장하지 못했어요. 잠시 후 다시 시도해 주세요';
		}
		busy = false;
	}
</script>

<section aria-label="자동 동기화" class="rounded-lg border border-border-subtle bg-surface-2 p-3">
	<div class="flex items-center justify-between">
		<h2 class="text-sm font-semibold text-fg-primary">자동 동기화</h2>
		<label class="flex items-center gap-2 text-xs text-fg-secondary">
			<input
				type="checkbox"
				checked={cur.enabled}
				disabled={busy}
				onchange={(e) => change({ enabled: e.currentTarget.checked })}
			/>
			{cur.enabled ? '켜짐' : '꺼짐'}
		</label>
	</div>
	<div class="mt-2 flex flex-wrap items-center gap-2 text-xs text-fg-secondary">
		<select
			aria-label="동기화 간격"
			class="rounded border border-border-subtle bg-surface-1 px-1 py-1"
			disabled={busy || !cur.enabled}
			value={cur.interval_h}
			onchange={(e) => change({ interval_h: Number(e.currentTarget.value) })}
		>
			{#each INTERVALS as h (h)}<option value={h}>{h}시간마다</option>{/each}
		</select>
		<select
			aria-label="동기화 범위"
			class="rounded border border-border-subtle bg-surface-1 px-1 py-1"
			disabled={busy || !cur.enabled}
			value={cur.window_days}
			onchange={(e) => change({ window_days: Number(e.currentTarget.value) })}
		>
			{#each WINDOWS.includes(cur.window_days) ? WINDOWS : [...WINDOWS, cur.window_days].sort((a, b) => a - b) as d (d)}
				<option value={d}>최근 {d}일</option>
			{/each}
		</select>
	</div>
	{#if cur.enabled}
		<p class="mt-2 text-xs text-fg-muted">
			{hm(cur.last_run_at) ? `마지막 ${hm(cur.last_run_at)}` : '아직 실행 전'}{hm(cur.next_run_at)
				? ` · 다음 ${hm(cur.next_run_at)}`
				: ''}
		</p>
	{/if}
	{#if error}<p class="mt-1 text-xs text-semantic-red" role="status">{error}</p>{/if}
</section>
