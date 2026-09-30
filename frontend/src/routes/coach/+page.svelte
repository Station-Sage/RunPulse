<script lang="ts">
	// 03e-coach.md 5-A — Coach 홈: 최근 대화 목록 + 새 대화 시작 + 플랜 섹션 + QuickInput.
	import type { CoachPageData } from './+page';
	import { createThread, putConsent, type ConsentInput } from '$lib/api/coach';
	import { postCheckin } from '$lib/api/today';
	import { ApiError } from '$lib/api/client';
	import { formatRelativeTime, weekProgressLabel } from '$lib/format';
	import { stripMarkdown } from '$lib/markdownLite';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import type { ChatThread, PainLevel, CheckinRow, CoachEngine, CoachChip } from '$lib/types';
	import QuickInput from '$lib/components/QuickInput.svelte';
	import DegradedBanner from '$lib/components/coach/DegradedBanner.svelte';
	import EngineLine from '$lib/components/coach/EngineLine.svelte';
	import ScopeSheet from '$lib/components/coach/ScopeSheet.svelte';
	import { needsConsent } from '$lib/coachEngine';
	import type { CoachInput } from '$lib/coachSuggestions';
	import { staleLabel, threadTitles } from '$lib/threadAge';

	let { data }: { data: CoachPageData } = $props();

	let threads = $state<ChatThread[]>(data.result?.threads ?? []);
	const titles = $derived(threadTitles(threads));
	let errorMessage = $state(data.errorMessage);

	// 새 대화 입력 상태
	let isCreating = $state(false);
	let newInput = $state('');
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

	let checkin = $state<CheckinRow | null>(data.checkin);
	let savingCheckin = $state(false);
	let checkinError = $state<string | null>(null);
	async function handleSaveCheckin(value: { fatigue?: number; pain?: PainLevel; note?: string }) {
		savingCheckin = true;
		checkinError = null;
		try {
			checkin = await postCheckin(value);
		} catch (e) {
			checkinError = e instanceof Error ? e.message : '저장에 실패했습니다.';
		} finally {
			savingCheckin = false;
		}
	}

	function openNew() {
		newInput = '';
		isCreating = true;
	}

	function submitNew() {
		const msg = newInput.trim();
		if (msg) start(msg);
	}

	// 칩 탭·자유 입력 모두 한 번에 스레드를 만들고 대화 화면으로 이동한다(design H3).
	async function start(input: CoachInput) {
		if (sending) return;
		if (needsConsent(engine)) {
			pendingInput = input;
			scopeOpen = true;
			return;
		}
		sending = true;
		errorMessage = null;
		try {
			const res = await createThread(input);
			await goto(`${base}/coach/${res.thread.id}?from=coach`);
		} catch (e) {
			errorMessage = e instanceof ApiError ? e.message : '대화를 시작할 수 없습니다.';
			sending = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		// 한글 IME 조합 중 Enter는 글자 확정용 — 전송하면 마지막 글자가 중복·누락된다.
		if (e.isComposing || e.keyCode === 229) return;
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			submitNew();
		}
	}
</script>

<svelte:head><title>Coach · RunPulse</title></svelte:head>

<div class="flex flex-col">
	<DegradedBanner {engine} />
	<!-- 최근 대화 섹션 -->
	<div class="border-b border-border-subtle px-4 py-3">
		<p class="text-xs uppercase tracking-wide text-fg-muted">최근 대화</p>
	</div>

	{#if errorMessage && threads.length === 0}
		<div class="flex flex-col items-center gap-2 px-4 py-10 text-center">
			<p class="text-fg-secondary">대화를 불러올 수 없습니다</p>
			<p class="text-xs text-fg-muted">{errorMessage}</p>
		</div>
	{:else if threads.length === 0}
		<div class="flex flex-col items-center gap-1 px-4 py-10 text-center">
			<p class="text-fg-secondary">아직 대화가 없습니다</p>
			<p class="text-sm text-fg-muted">아래에서 새 대화를 시작해 보세요.</p>
		</div>
	{:else}
		<ul class="divide-y divide-border-subtle">
			{#each threads as t (t.id)}
				<li>
					<a
						href="{base}/coach/{t.id}"
						class="flex items-center gap-3 px-4 py-3 hover:bg-surface-2 active:bg-surface-3"
					>
						<div class="min-w-0 flex-1">
							<p class="truncate text-sm font-medium">{titles.get(t.id) ?? t.title}</p>
							{#if t.last_message}
								<p class="line-clamp-2 text-xs text-fg-muted">{stripMarkdown(t.last_message)}</p>
							{/if}
							{#if staleLabel(t.last_message_at, Date.now())}
								<p class="text-[10px] text-semantic-amber">{staleLabel(t.last_message_at, Date.now())}</p>
							{/if}
						</div>
						{#if t.last_message_at}
							<span class="shrink-0 text-xs text-fg-muted"
								>{formatRelativeTime(t.last_message_at)}</span
							>
						{/if}
						<span class="text-fg-muted">›</span>
					</a>
				</li>
			{/each}
		</ul>
	{/if}

	<!-- 새 대화 입력 폼 (토글) -->
	{#if isCreating}
		<div class="border-t border-border-subtle px-4 py-3">
			<textarea
				bind:value={newInput}
				onkeydown={handleKeydown}
				placeholder="무엇이든 물어보세요…"
				rows={3}
				disabled={sending}
				class="w-full resize-none rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 text-sm text-fg-primary placeholder:text-fg-muted focus:outline-none disabled:opacity-50"
			></textarea>
			<div class="mt-1">
				<EngineLine {engine} onOpenScope={() => (scopeOpen = true)} />
			</div>
			<div class="mt-2 flex justify-end gap-2">
				<button
					type="button"
					onclick={() => {
						isCreating = false;
						newInput = '';
					}}
					disabled={sending}
					class="rounded-lg border border-border-subtle px-4 py-2 text-sm text-fg-secondary disabled:opacity-50"
				>
					취소
				</button>
				<button
					type="button"
					onclick={submitNew}
					disabled={sending || !newInput.trim()}
					class="rounded-lg bg-fg-primary px-4 py-2 text-sm text-surface-1 disabled:opacity-40"
				>
					{sending ? '전송 중…' : '전송'}
				</button>
			</div>
			{#if errorMessage}
				<p class="mt-1 text-xs text-semantic-red">{errorMessage}</p>
			{/if}
		</div>
	{:else}
		<!-- + 새 대화 시작 버튼 -->
		<div class="flex justify-center px-4 py-4">
			<button
				type="button"
				onclick={() => openNew()}
				class="rounded-lg border border-border-subtle bg-surface-2 px-6 py-2.5 text-sm font-medium text-fg-primary"
			>
				+ 새 대화 시작
			</button>
		</div>
	{/if}

	<!-- 지금 답할 수 있는 질문 (서버가 데이터 있는 칩만 제공) -->
	{#if !isCreating}
		{#if chips.length > 0}
			<div class="border-t border-border-subtle px-4 py-3">
				<p class="mb-2 text-xs uppercase tracking-wide text-fg-muted">바로 물어보기</p>
				<div class="flex flex-wrap gap-2">
					{#each chips as chip (chip.chip_id)}
						<button
							type="button"
							data-testid="home-chip"
							onclick={() => start(chip)}
							disabled={sending}
							class="rounded-full border border-border-subtle bg-surface-2 px-3 py-1 text-sm text-fg-secondary hover:bg-surface-3 disabled:opacity-50"
						>
							{chip.text}
						</button>
					{/each}
				</div>
				{#if sending}
					<p class="mt-2 text-xs text-fg-muted">답변을 준비하고 있어요…</p>
				{:else if errorMessage}
					<p class="mt-2 text-xs text-semantic-red">{errorMessage}</p>
				{/if}
			</div>
		{/if}

		<!-- 플랜 섹션 -->
		<div class="border-t border-border-subtle px-4 py-3">
			<p class="mb-1 text-xs uppercase tracking-wide text-fg-muted">플랜</p>
			{#if data.activePlan}
				<a
					href="{base}/coach/plan/{data.activePlan.goal.id}"
					class="flex items-center justify-between rounded-lg bg-surface-2 px-3 py-2 hover:bg-surface-3"
				>
					<div class="min-w-0">
						<p class="truncate text-sm font-medium">{data.activePlan.goal.name}</p>
						<p class="text-xs text-fg-muted">
							진행 중: {weekProgressLabel(data.activePlan.week_index, data.activePlan.goal.plan_weeks)}
						</p>
					</div>
					<span class="ml-2 shrink-0 text-fg-muted">›</span>
				</a>
			{:else}
				<a
					href="{base}/coach/plan/new"
					class="text-sm text-semantic-amber hover:underline"
				>
					새 프로그램 만들기 →
				</a>
			{/if}
		</div>

		<!-- QuickInput 체크인 섹션 -->
		<div class="flex flex-col gap-1 border-t border-border-subtle px-4 py-3">
			<QuickInput
				compact
				existing={checkin
					? {
							fatigue: checkin.fatigue ?? undefined,
							pain: checkin.pain ?? undefined,
							note: checkin.note ?? undefined,
							timestamp: checkin.created_at
						}
					: undefined}
				saving={savingCheckin}
				onSave={handleSaveCheckin}
			/>
			<p class="text-xs text-fg-muted">입력한 컨디션은 오늘 훈련 답변에 반영됩니다.</p>
			{#if checkinError}
				<p class="text-xs text-semantic-red">{checkinError}</p>
			{/if}
		</div>
	{/if}
</div>

{#if scopeOpen && engine}
	<ScopeSheet {engine} requireConsent={needsConsent(engine)} onSave={saveConsent} onClose={closeScope} />
{/if}
