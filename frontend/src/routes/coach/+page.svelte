<script lang="ts">
	import PageHead from '$lib/components/ui/PageHead.svelte';
	// 03e-coach.md 5-A — Coach 홈: 최근 대화 목록 + 새 대화 시작 + 플랜 섹션 + QuickInput.
	import type { CoachPageData } from './+page';
	import { createThread, newClientMsgId, putConsent, type ConsentInput } from '$lib/api/coach';
	import { ApiError } from '$lib/api/client';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import type { ChatThread, CoachEngine, CoachChip } from '$lib/types';
	import DegradedBanner from '$lib/components/coach/DegradedBanner.svelte';
	import ThreadList from '$lib/components/coach/ThreadList.svelte';
	import NewThreadForm from '$lib/components/coach/NewThreadForm.svelte';
	import CoachStartChips from '$lib/components/coach/CoachStartChips.svelte';
	import CoachPlanCard from '$lib/components/coach/CoachPlanCard.svelte';
	import CoachCheckin from '$lib/components/coach/CoachCheckin.svelte';
	import ScopeSheet from '$lib/components/coach/ScopeSheet.svelte';
	import { needsConsent } from '$lib/coachEngine';
	import { inputText as chipLabel, type CoachInput } from '$lib/coachSuggestions';
	import { smallDataTodos, evidenceLimitNotice } from '$lib/coachSmallData';
	import { threadTitles } from '$lib/threadAge';

	let { data }: { data: CoachPageData } = $props();

	let threads = $state<ChatThread[]>(data.result?.threads ?? []);
	const titles = $derived(threadTitles(threads));
	let errorMessage = $state<string | null>(null);

	let isCreating = $state(false);
	let sending = $state(false);
	let engine = $state<CoachEngine | null>(data.engine);
	let scopeOpen = $state(false);
	let pendingInput = $state<CoachInput | null>(null);

	async function saveConsent(input: ConsentInput) {
		const consent = await putConsent(input);
		if (engine) engine = { ...engine, consent };
		scopeOpen = false;
		if (pendingInput) {
			const input = pendingInput;
			pendingInput = null;
			start(input);
		}
	}

	function closeScope() {
		scopeOpen = false;
		pendingInput = null;
	}

	const chips: CoachChip[] = data.suggestions;
	const todos = smallDataTodos(data.unlock);
	const limitNotice = evidenceLimitNotice(data.unlock);

	// 칩 탭·자유 입력 모두 한 번에 스레드를 만들고 대화 화면으로 이동한다(design H3).
	let retry: { key: string; id: string } | null = null;

	async function start(input: CoachInput) {
		if (sending) return;
		if (needsConsent(engine)) {
			pendingInput = input;
			scopeOpen = true;
			return;
		}
		sending = true;
		errorMessage = null;
		// 실패 후 재시도해도 같은 id — 서버가 중복 생성을 막는다.
		const key = chipLabel(input);
		if (retry?.key !== key) retry = { key, id: newClientMsgId() };
		try {
			const res = await createThread(input, retry.id);
			await goto(`${base}/coach/${res.thread.id}?from=coach`);
		} catch (e) {
			errorMessage = e instanceof ApiError ? e.message : '대화를 시작할 수 없습니다.';
			sending = false;
		}
	}
</script>

<PageHead title="Coach" heading={null} />

<h1 class="sr-only">Coach</h1>

<div class="flex flex-col">
	<DegradedBanner {engine} />
	<div class="border-b border-border-subtle px-4 py-3">
		<h2 class="text-xs uppercase tracking-wide text-fg-muted">최근 대화</h2>
	</div>

	<ThreadList {threads} {titles} failure={data.threadsFailure} />

	{#if isCreating}
		<NewThreadForm
			{engine}
			{sending}
			{errorMessage}
			onSubmit={start}
			onCancel={() => (isCreating = false)}
			onOpenScope={() => (scopeOpen = true)}
		/>
	{:else}
		<div class="flex justify-center px-4 py-4">
			<button
				type="button"
				onclick={() => (isCreating = true)}
				class="min-h-11 rounded-lg border border-border-subtle bg-surface-2 px-6 py-2.5 text-sm font-medium text-fg-primary"
			>
				+ 새 대화 시작
			</button>
		</div>
		<CoachStartChips {todos} {chips} {limitNotice} {sending} {errorMessage} onStart={start} />
		<CoachPlanCard activePlan={data.activePlan} />
		<CoachCheckin initial={data.checkin} />
	{/if}
</div>

{#if scopeOpen && engine}
	<ScopeSheet {engine} requireConsent={needsConsent(engine)} onSave={saveConsent} onClose={closeScope} />
{/if}
