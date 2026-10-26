<script lang="ts">
	// 지금 답할 수 있는 질문 — 데이터 부족 시 할 일(todos), 아니면 서버 칩.
	import { base } from '$app/paths';
	import type { CoachChip } from '$lib/types';
	import type { CoachInput } from '$lib/coachSuggestions';
	import type { SmallDataTodo } from '$lib/coachSmallData';

	let {
		todos,
		chips,
		limitNotice,
		sending,
		errorMessage,
		onStart
	}: {
		todos: SmallDataTodo[];
		chips: CoachChip[];
		limitNotice: string | null;
		sending: boolean;
		errorMessage: string | null;
		onStart: (input: CoachInput) => void;
	} = $props();
</script>

{#snippet status()}
	{#if sending}
		<p class="mt-2 text-xs text-fg-muted">답변을 준비하고 있어요…</p>
	{:else if errorMessage}
		<p class="mt-2 text-xs text-semantic-red">{errorMessage}</p>
	{/if}
{/snippet}

{#if todos.length > 0}
	<div class="border-t border-border-subtle px-4 py-3" data-testid="coach-small-data">
		<p class="mb-1 text-xs uppercase tracking-wide text-fg-muted">데이터 모이는 동안 할 일</p>
		{#if limitNotice}<p class="mb-2 text-xs text-fg-muted">{limitNotice}</p>{/if}
		<div class="flex flex-wrap gap-2">
			{#each todos as todo (todo.id)}
				{#if todo.kind === 'chat'}
					<button type="button" onclick={() => onStart(todo.target)} disabled={sending} class="rounded-full border border-border-subtle bg-surface-2 px-3 py-1 text-sm text-fg-secondary hover:bg-surface-3 disabled:opacity-50">{todo.label}</button>
				{:else}
					<a href="{base}{todo.target}" class="rounded-full border border-border-subtle bg-surface-2 px-3 py-1 text-sm text-fg-secondary hover:bg-surface-3">{todo.label}</a>
				{/if}
			{/each}
		</div>
		{@render status()}
	</div>
{:else if chips.length > 0}
	<div class="border-t border-border-subtle px-4 py-3">
		<p class="mb-2 text-xs uppercase tracking-wide text-fg-muted">바로 물어보기</p>
		<div class="flex flex-wrap gap-2">
			{#each chips as chip (chip.chip_id)}
				<button
					type="button"
					data-testid="home-chip"
					onclick={() => onStart(chip)}
					disabled={sending}
					class="rounded-full border border-border-subtle bg-surface-2 px-3 py-1 text-sm text-fg-secondary hover:bg-surface-3 disabled:opacity-50"
				>
					{chip.text}
				</button>
			{/each}
		</div>
		{@render status()}
	</div>
{/if}
