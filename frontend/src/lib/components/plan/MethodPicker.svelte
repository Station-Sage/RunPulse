<script lang="ts">
	import { methodOrder } from '$lib/replanView';
	import type { PlanMethodInfo, PlanMethodRecommend } from '$lib/types/planMethods';

	let {
		methods,
		current,
		selected,
		rec,
		onselect
	}: {
		methods: PlanMethodInfo[];
		current: string;
		selected: string;
		rec: PlanMethodRecommend | null;
		onselect: (id: string) => void;
	} = $props();

	let open = $state(false);
	const ordered = $derived(methodOrder(methods, rec));
	const top = $derived(ordered.find((m) => m.id === rec?.recommended) ?? ordered[0]);
	const others = $derived(ordered.filter((m) => m.id !== top?.id));
</script>

{#snippet card(m: PlanMethodInfo, isRec: boolean)}
	<div class="rounded-lg border p-3 text-xs {selected === m.id ? 'border-fg-primary' : 'border-border'} bg-surface-1" data-testid="method-card-{m.id}">
		<div class="flex flex-wrap items-center gap-2">
			<span class="text-sm font-medium text-fg-primary">{m.label}</span>
			{#if m.id === current}<span class="rounded-full bg-surface-2 px-2 py-0.5">현재</span>{/if}
			{#if isRec}<span class="rounded-full bg-surface-2 px-2 py-0.5">{rec?.source === 'ai' ? 'AI 추천' : '추천'}</span>{/if}
		</div>
		<p class="mt-1 text-fg-secondary">{m.summary}</p>
		{#if isRec && rec?.reasons[m.id]}<p class="mt-1 text-fg-primary">{rec.reasons[m.id]}</p>{/if}
		{#if rec?.warnings[m.id]}<p class="mt-1 text-semantic-red">{rec.warnings[m.id]}</p>{/if}
		<p class="mt-2 text-fg-secondary">추천 대상: {m.target_runners}</p>
		<ul class="mt-1 list-disc pl-4 text-fg-secondary">
			{#each m.pros as t}<li>장점: {t}</li>{/each}
			{#each m.cons as t}<li>단점: {t}</li>{/each}
		</ul>
		<button
			type="button"
			class="mt-2 min-h-11 w-full rounded-lg px-4 text-sm {selected === m.id ? 'bg-fg-primary text-surface-1' : 'bg-surface-2 text-fg-primary'}"
			aria-pressed={selected === m.id}
			onclick={() => onselect(m.id)}
		>
			{selected === m.id ? '선택됨' : '이 방식으로'}
		</button>
	</div>
{/snippet}

<section class="space-y-2 rounded-lg bg-surface-2 p-3" aria-label="훈련 방식" data-testid="method-picker">
	<p class="text-sm font-medium text-fg-primary">훈련 방식</p>
	{#if rec?.pending}<p class="text-xs text-fg-secondary">AI가 내 기록으로 추천을 계산하고 있어요. 지금은 규칙 기반 추천이에요.</p>{/if}
	{#if top}{@render card(top, true)}{/if}
	{#if others.length}
		<details bind:open>
			<summary class="min-h-11 cursor-pointer py-3 text-xs text-fg-secondary">다른 방식 보기 ({others.length})</summary>
			<div class="space-y-2">
				{#each others as m (m.id)}{@render card(m, false)}{/each}
			</div>
		</details>
	{/if}
</section>
