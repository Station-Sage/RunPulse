<script lang="ts">
	// 활동에서 시작하는 새 대화 — 근거 카드 + 유형별 추천 질문 3개 + 자유 입력(20 design §코치에게 묻기).
	import type { CoachNewPageData } from './+page';
	import { createThread, newClientMsgId, putConsent, type ConsentInput } from '$lib/api/coach';
	import { ApiError } from '$lib/api/client';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import type { CoachEngine } from '$lib/types';
	import DegradedBanner from '$lib/components/coach/DegradedBanner.svelte';
	import ScopeSheet from '$lib/components/coach/ScopeSheet.svelte';
	import ChatComposer from '$lib/components/coach/ChatComposer.svelte';
	import { needsConsent } from '$lib/coachEngine';
	import { evidenceChips } from '$lib/activityEvidence';
	import { metricContextRef } from '$lib/coachMetricPrefill';

	let { data }: { data: CoachNewPageData } = $props();

	const activity = $derived(data.activity);
	const metric = $derived(data.metric);
	const suggestions = $derived(metric ? metric.suggestions : (activity?.suggestions ?? []));
	const hasContext = $derived((data.activityId != null && activity != null) || metric != null);
	const chips = $derived(activity ? evidenceChips(activity) : []);
	let engine = $state<CoachEngine | null>(data.engine);
	let input = $state('');
	let sending = $state(false);
	let errorMessage = $state<string | null>(null);
	let scopeOpen = $state(false);
	let pendingText = $state<string | null>(null);
	let retry: { key: string; id: string } | null = null;

	async function start(text: string) {
		const msg = text.trim();
		if (!msg || sending || !hasContext) return;
		if (needsConsent(engine)) {
			pendingText = msg;
			scopeOpen = true;
			return;
		}
		sending = true;
		errorMessage = null;
		if (retry?.key !== msg) retry = { key: msg, id: newClientMsgId() };
		try {
			const ctx = metric ? { kind: 'metric', ref: metricContextRef(metric) } : { kind: 'activity', ref: String(data.activityId) };
			const res = await createThread(msg, retry.id, ctx);
			await goto(`${base}/coach/${res.thread.id}?from=${metric ? 'metric' : 'activity'}`);
		} catch (e) {
			errorMessage = e instanceof ApiError ? e.message : '대화를 시작할 수 없습니다.';
			sending = false;
		}
	}

	async function saveConsent(value: ConsentInput) {
		const consent = await putConsent(value);
		if (engine) engine = { ...engine, consent };
		scopeOpen = false;
		const text = pendingText;
		pendingText = null;
		if (text) start(text);
	}

	function closeScope() {
		scopeOpen = false;
		pendingText = null;
	}
</script>

<svelte:head><title>코치에게 묻기 · RunPulse</title></svelte:head>

<div class="flex min-h-[calc(100dvh-8rem)] flex-col">
	<DegradedBanner {engine} />
	<div class="flex items-center gap-2 border-b border-border-subtle px-4 py-3">
		<a href={metric ? `${base}/library/metrics/${metric.slug}?date=${metric.date}` : data.activityId != null ? `${base}/library/${data.activityId}` : `${base}/coach`} class="shrink-0 text-fg-muted" aria-label="활동으로" data-testid="new-back">←</a>
		<h1 class="min-w-0 flex-1 truncate text-base font-semibold">코치에게 묻기</h1>
	</div>

	{#if !hasContext}
		<div class="flex flex-col items-center gap-2 px-4 py-10 text-center" data-testid="activity-missing">
			<p class="text-fg-secondary">활동 정보를 불러올 수 없습니다</p>
			<a href="{base}/coach" class="text-sm text-fg-secondary underline">← Coach로</a>
		</div>
	{:else}
		<div class="flex flex-1 flex-col gap-4 px-4 py-4">
			<section class="rounded-lg border border-border-subtle bg-surface-2 p-3" data-testid="evidence-card">
				{#if metric}
					<p class="text-xs text-fg-muted">대화 대상 지표</p>
					<p class="mt-1 text-sm font-medium text-fg-primary" data-testid="metric-card">{metric.date} {metric.name} {metric.valueText}</p>
				{:else if activity}
				<p class="text-xs text-fg-muted">대화 대상 활동</p>
				<p class="mt-1 text-sm font-medium text-fg-primary">
					{activity.date ?? ''} {activity.workout_class_label ?? ''} {activity.name ?? ''}
				</p>
				{/if}
				{#if !metric && chips.length > 0}
					<div class="mt-2 flex flex-wrap gap-2">
						{#each chips as c (c)}
							<span class="rounded-full border border-border-subtle px-2.5 py-0.5 text-xs text-fg-secondary" data-testid="evidence-chip">{c}</span>
						{/each}
					</div>
				{/if}
			</section>

			<section class="flex flex-col gap-2">
				<p class="text-xs uppercase tracking-wide text-fg-muted">이런 걸 물어볼 수 있어요</p>
				{#each suggestions as q (q)}
					<button type="button" disabled={sending} onclick={() => start(q)} class="rounded-lg border border-border-subtle bg-surface-2 px-3 py-3 text-left text-sm text-fg-primary disabled:opacity-40" data-testid="suggested-question">{q}</button>
				{/each}
			</section>

			{#if errorMessage}
				<p class="text-xs text-red-400" role="alert">{errorMessage}</p>
			{/if}
		</div>
		<ChatComposer {engine} bind:value={input} busy={sending} onSend={() => start(input)} onOpenScope={() => (scopeOpen = true)} />
	{/if}
</div>

{#if scopeOpen && engine}
	<ScopeSheet {engine} requireConsent={needsConsent(engine)} onSave={saveConsent} onClose={closeScope} />
{/if}
