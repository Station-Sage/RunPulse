<script lang="ts">
	// S12 — 훈련 이야기(월·주). 문단·칩·직전 기간 비교·강도 분포·대표 세션·위험 최고·마일스톤.
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import type { StoryData } from '$lib/api/story';
	import { isoWeekId, storyScope } from '$lib/storyPeriod';

	let { data }: { data: { story: StoryData } } = $props();
	const s = $derived(data.story);
	const scope = $derived(storyScope(s.period.id));
	const unitLabel = $derived(scope === 'week' ? '주' : scope === 'block' ? '블록' : '달');
	let copied = $state(false);

	const open = (id: string) => goto(`${base}/library/story/${id}`, { replaceState: true });
	const toMonth = () => open(s.period.end.slice(0, 7));
	const toWeek = () => open(isoWeekId(s.period.end));

	async function copyText() {
		const text = `${s.period.label}\n\n${s.paragraph}\n\n${s.chips.map((c) => c.label).join(' · ')}`;
		await navigator.clipboard.writeText(text);
		copied = true;
		setTimeout(() => (copied = false), 2000);
	}

	const bars = $derived(
		s.intensity?.status === 'ok'
			? [
					['Z1-2', s.intensity.z12_pct ?? 0, 'bg-sky-400'],
					['Z3', s.intensity.z3_pct ?? 0, 'bg-amber-400'],
					['Z4-5', s.intensity.z45_pct ?? 0, 'bg-rose-400']
				]
			: []
	);
	const sign = (n: number) => (n > 0 ? '+' : '');
</script>

<div class="mx-auto flex max-w-2xl flex-col gap-5 p-4">
	<header class="flex flex-col gap-2">
		<div class="flex items-center justify-between">
			<button class="px-3 py-2" aria-label="이전 {unitLabel}" onclick={() => open(s.period.prev)}>‹</button>
			<div class="text-center">
				<div class="text-lg font-semibold text-fg-primary">{s.period.label}</div>
				<div class="text-xs text-fg-muted">{s.period.start} ~ {s.period.end}</div>
			</div>
			<button class="px-3 py-2" aria-label="다음 {unitLabel}" onclick={() => open(s.period.next)}>›</button>
		</div>
		<div class="flex gap-1 text-sm" role="group" aria-label="단위">
			<button class="flex-1 rounded px-2 py-1 {scope === 'month' ? 'bg-surface-2 font-semibold' : ''}" aria-pressed={scope === 'month'} onclick={toMonth}>월</button>
			<button class="flex-1 rounded px-2 py-1 {scope === 'week' ? 'bg-surface-2 font-semibold' : ''}" aria-pressed={scope === 'week'} onclick={toWeek}>주</button>
		</div>
	</header>

	<p class="rounded bg-surface-2 p-4 leading-relaxed text-fg-primary">{s.paragraph}</p>

	{#if s.chips.length}
		<div class="flex flex-wrap gap-2">
			{#each s.chips as c (c.label)}
				<span class="rounded-full border border-border-subtle px-3 py-1 text-sm text-fg-secondary">{c.label}</span>
			{/each}
		</div>
	{/if}

	{#if s.compare.length}
		<section>
			<h3 class="mb-2 text-sm font-semibold text-fg-secondary">이전 {unitLabel}과 비교</h3>
			<ul class="flex flex-col gap-2">
				{#each s.compare as c (c.key)}
					<li class="flex items-center justify-between rounded bg-surface-2 p-2 text-sm">
						<span>{c.label}</span>
						<span class="text-right">
							<span class="font-semibold">{c.value}</span>
							<span class="block text-xs text-fg-muted">{sign(c.delta_pct)}{c.delta_pct}% (이전 {c.prev})</span>
						</span>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if s.intensity}
		<section>
			<h3 class="mb-2 text-sm font-semibold text-fg-secondary">강도 분포</h3>
			{#if s.intensity.status === 'insufficient'}
				<p class="rounded bg-surface-2 p-3 text-sm text-fg-muted">심박 존 데이터가 부족해 분포를 보여줄 수 없어요.</p>
			{:else}
				<div class="flex flex-col gap-2">
					{#each bars as [label, pct, color] (label)}
						<div class="flex items-center gap-2 text-sm">
							<span class="w-12">{label}</span>
							<div class="h-5 flex-1 rounded bg-surface-2"><div class="h-full rounded {color}" style="width: {pct}%"></div></div>
							<span class="w-10 text-right">{pct}%</span>
						</div>
					{/each}
				</div>
			{/if}
		</section>
	{/if}

	{#if s.key_sessions.length}
		<section>
			<h3 class="mb-2 text-sm font-semibold text-fg-secondary">대표 세션</h3>
			<ul class="flex flex-col gap-2">
				{#each s.key_sessions as k (k.id)}
					<li>
						<a class="block rounded bg-surface-2 p-3 text-sm" href="{base}/library/{k.id}">
							<span class="font-semibold">{k.name}</span>
							<span class="block text-fg-muted">{k.date} · {k.distance_km}km</span>
						</a>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if s.risk_peak}
		<p class="rounded border border-border-subtle p-3 text-sm">
			<span class="font-semibold">위험 최고</span>
			{s.risk_peak.slug.toUpperCase()} {s.risk_peak.value} ({s.risk_peak.date})
		</p>
	{/if}

	{#if s.milestones.length}
		<section>
			<h3 class="mb-2 text-sm font-semibold text-fg-secondary">마일스톤</h3>
			<ul class="flex flex-col gap-2">
				{#each s.milestones as m, i (m.id ?? i)}
					<li class="rounded bg-surface-2 p-3 text-sm">
						<span class="font-semibold">◆ {m.title ?? m.label}</span>
						<span class="block text-fg-muted">{m.achieved_date ?? m.date}</span>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	<button class="rounded border border-border-subtle px-3 py-2 text-sm" onclick={copyText}>
		{copied ? '복사됨' : '텍스트로 복사'}
	</button>
</div>
