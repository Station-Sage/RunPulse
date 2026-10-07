<script lang="ts">
	import { patchProfile, type ProfileRow, type ProfileSource } from '$lib/api/data';
	import {
		PROFILE_LABEL,
		SOURCE_LABEL,
		formatProfileValue,
		parseProfileInput
	} from '$lib/profileRows';

	let { row, onSaved }: { row: ProfileRow; onSaved: (rows: ProfileRow[]) => void } = $props();
	let input = $state('');
	let busy = $state(false);
	let error = $state<string | null>(null);
	let editing = $state(false);

	const SRC: ProfileSource[] = ['self', 'device', 'manual'];
	const valueOf = (s: ProfileSource) => row[s]?.value ?? null;
	const hint = (s: ProfileSource) =>
		s === 'self' && row.self
			? row.self.at
				? `${row.self.at} 기준`
				: '최근 30일 중앙값'
			: s === 'device' && row.device
				? `${row.device.provider} · ${row.device.at}`
				: null;

	async function save(changes: Parameters<typeof patchProfile>[0]) {
		if (busy) return;
		busy = true;
		error = null;
		try {
			onSaved((await patchProfile(changes)).rows);
			editing = false;
		} catch (e) {
			error = e instanceof Error && e.message ? e.message : '저장하지 못했어요. 잠시 후 다시 시도해 주세요';
		}
		busy = false;
	}

	function saveManual() {
		const v = parseProfileInput(row.key, input);
		if (v === undefined) {
			error = '숫자로 입력해 주세요 (페이스는 5:05 형식)';
			return;
		}
		save(
			v === null
				? { overrides: { [row.key]: null } }
				: { overrides: { [row.key]: v }, source_choice: { [row.key]: 'manual' } }
		);
	}
</script>

<section aria-label={PROFILE_LABEL[row.key]} class="rounded-lg border border-border-subtle bg-surface-2 p-3">
	<h2 class="text-sm font-semibold text-fg-primary">{PROFILE_LABEL[row.key]}</h2>
	<ul class="mt-2 flex flex-col gap-1">
		{#each SRC as s (s)}
			{@const v = valueOf(s)}
			<li>
				<label class="flex items-center gap-2 text-xs {v == null ? 'text-fg-muted' : 'text-fg-secondary'}">
					<input
						type="radio"
						name="src-{row.key}"
						checked={row.using === s}
						disabled={busy || v == null}
						onchange={() => save({ source_choice: { [row.key]: s } })}
					/>
					<span class="w-16">{SOURCE_LABEL[s]}</span>
					<span class="text-fg-primary">{formatProfileValue(row.key, v)}</span>
					{#if hint(s)}<span class="text-fg-muted">{hint(s)}</span>{/if}
				</label>
			</li>
		{/each}
	</ul>
	{#if editing}
		<div class="mt-2 flex items-center gap-2">
			<input
				aria-label="{PROFILE_LABEL[row.key]} 직접 입력"
				class="w-28 rounded border border-border-subtle bg-surface-1 px-2 py-1 text-xs"
				bind:value={input}
				placeholder={row.key === 'threshold_pace' ? '5:05' : '숫자'}
			/>
			<button type="button" class="text-xs text-fg-primary" disabled={busy} onclick={saveManual}>저장</button>
			<button type="button" class="text-xs text-fg-muted" onclick={() => (editing = false)}>취소</button>
		</div>
	{:else}
		<button
			type="button"
			class="mt-2 text-xs text-fg-secondary underline"
			onclick={() => {
				input = row.manual ? String(row.manual.value) : '';
				editing = true;
			}}>직접 입력{row.manual ? ' 수정' : ''}</button
		>
	{/if}
	{#if error}<p class="mt-1 text-xs text-semantic-red" role="status">{error}</p>{/if}
</section>
