<script lang="ts">
	// C5 — 04-component-catalog.md. 피로도·통증·메모 빠른 입력(P6 One Finger Reach).
	// 키보드 단축키(R/P/N)는 이번 1차 범위에서 뺐다 — 메모 입력 중 타이핑과 충돌 위험이
	// 있어 별도 검토가 필요해서다(DONE 기록 참조).
	import type { PainLevel, QuickInputProps } from '$lib/types';

	let { existing, compact = false, saving = false, onSave }: QuickInputProps = $props();

	const FATIGUE_LEVELS = Array.from({ length: 10 }, (_, i) => i + 1);
	const PAIN_LEVELS: { value: PainLevel; label: string }[] = [
		{ value: 'none', label: '없음' },
		{ value: 'mild', label: '경미' },
		{ value: 'moderate', label: '중간' },
		{ value: 'severe', label: '심함' }
	];

	// existing은 부모가 소유하는 prop이다 — 초기값은 $effect에서 한 번 당겨오고,
	// 그 이후엔 로컬 편집을 덮어쓰지 않는다(existing이 실제로 바뀔 때만 재동기화).
	let fatigue = $state<number | undefined>(undefined);
	let pain = $state<PainLevel | undefined>(undefined);
	let note = $state('');
	// compact는 접힌 한 줄로 시작한다(기존 값이 있으면 요약, 없으면 '오늘 컨디션 입력 →') — 탭하면 편집.
	let editing = $state(!compact);

	$effect(() => {
		if (existing?.fatigue !== undefined || existing?.pain || existing?.note) {
			fatigue = existing.fatigue;
			pain = existing.pain;
			note = existing.note ?? '';
			editing = false;
		}
	});

	const hasExisting = $derived(
		existing?.fatigue !== undefined || !!existing?.pain || !!existing?.note
	);

	const painLabel = $derived(PAIN_LEVELS.find((p) => p.value === existing?.pain)?.label ?? '');

	function handleSave() {
		onSave?.({ fatigue, pain, note: note || undefined });
	}
</script>

{#if compact && !editing}
	{#if hasExisting}
		<button
			type="button"
			onclick={() => (editing = true)}
			class="w-full rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 text-left text-sm text-fg-secondary hover:bg-surface-3"
		>
			피로 {existing?.fatigue ?? '—'} · 통증 {painLabel || '—'} ✓
		</button>
	{:else}
		<button
			type="button"
			onclick={() => (editing = true)}
			class="w-full rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 text-left text-sm text-fg-secondary hover:bg-surface-3"
		>
			오늘 컨디션 입력 →
		</button>
	{/if}
{:else}
	<div class="flex flex-col gap-3 rounded-lg border border-border-subtle bg-surface-2 p-4">
		<p class="text-sm text-fg-secondary">어떻게 느껴지나요?</p>

		<p class="text-xs text-fg-muted">피로도</p>
		<div role="radiogroup" aria-label="피로도 (1 가뿐함 ~ 10 매우 피곤)" class="grid grid-cols-10 gap-1">
			{#each FATIGUE_LEVELS as n (n)}
				<button
					type="button"
					aria-pressed={fatigue === n}
					aria-label={`피로도 ${n}`}
					onclick={() => (fatigue = n)}
					class="h-11 w-full rounded border border-border-subtle text-sm {fatigue === n
						? 'bg-semantic-teal text-white'
						: 'bg-surface-1 text-fg-secondary hover:bg-surface-3'}"
				>
					{n}
				</button>
			{/each}
		</div>
		<div class="-mt-2 flex justify-between text-xs text-fg-muted" aria-hidden="true">
			<span>1 가뿐함</span>
			<span>10 매우 피곤</span>
		</div>

		<div role="radiogroup" aria-label="통증 수준" class="flex flex-wrap gap-1">
			{#each PAIN_LEVELS as p (p.value)}
				<button
					type="button"
					aria-pressed={pain === p.value}
					aria-label={p.label}
					onclick={() => (pain = p.value)}
					class="rounded border border-border-subtle px-3 py-1.5 text-sm {pain === p.value
						? 'bg-semantic-amber text-white'
						: 'bg-surface-1 text-fg-secondary hover:bg-surface-3'}"
				>
					{p.label}
				</button>
			{/each}
		</div>

		<textarea
			bind:value={note}
			placeholder="메모 (선택)"
			rows="2"
			class="rounded border border-border-subtle bg-surface-1 px-2 py-1.5 text-sm text-fg-primary placeholder:text-fg-muted"
		></textarea>

		<div class="flex justify-end">
			<button
				type="button"
				onclick={handleSave}
				disabled={saving}
				class="rounded bg-semantic-teal px-4 py-1.5 text-sm font-medium text-white disabled:opacity-60"
			>
				{saving ? '저장 중…' : '저장'}
			</button>
		</div>
	</div>
{/if}
