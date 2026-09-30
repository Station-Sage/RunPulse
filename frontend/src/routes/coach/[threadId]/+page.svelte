<script lang="ts">
	// 03e-coach.md 5-B — 대화 스레드: 메시지 목록 + 입력 바.
	// P7-IMPL-COACH-EVIDENCE-UI: 근거 칩(EvidenceQuote) + MetricBreakdown 드릴다운 + 입력창 하단 도킹.
	import type { ThreadPageData } from './+page';
	import { addMessage, putConsent, regenerateMessage, type ConsentInput } from '$lib/api/coach';
	import { ApiError } from '$lib/api/client';
	import { base } from '$app/paths';
	import type { AnswerEvidence, ChatMessage, CoachEngine } from '$lib/types';
	import { goto } from '$app/navigation';
	import MessageBlock from '$lib/components/coach/MessageBlock.svelte';
	import EngineLine from '$lib/components/coach/EngineLine.svelte';
	import ScopeSheet from '$lib/components/coach/ScopeSheet.svelte';
	import EngineSheet from '$lib/components/coach/EngineSheet.svelte';
	import MetricBreakdown from '$lib/components/MetricBreakdown.svelte';
	import DrillPanel from '$lib/components/DrillPanel.svelte';
	import { needsConsent } from '$lib/coachEngine';
	import type { DrillTarget } from '$lib/evidence';
	import { chipTarget } from '$lib/answerEvidence';
	import { inputText as chipLabel, type CoachInput } from '$lib/coachSuggestions';
	import { EXPLAIN_SUPPORTED_SLUGS } from '$lib/api/metrics';
	import { openDrill } from '$lib/drillStack';
	import { localDateString } from '$lib/asOf';

	let { data }: { data: ThreadPageData } = $props();

	const thread = $derived(data.detail?.thread ?? null);
	let messages = $state<ChatMessage[]>(data.detail?.messages ?? []);
	let errorMessage = $state(data.errorMessage);
	let engine = $state<CoachEngine | null>(data.engine);

	// 첫 LLM 전송 동의 게이트 — 동의 전에는 send를 보류하고 시트를 띄운다.
	let scopeOpen = $state(false);
	let afterConsent = $state<(() => void) | null>(null);
	let reasonMsg = $state<ChatMessage | null>(null);
	let regeneratingId = $state<number | null>(null);

	async function saveConsent(input: ConsentInput) {
		const consent = await putConsent(input);
		if (engine) engine = { ...engine, consent };
		scopeOpen = false;
		const next = afterConsent;
		afterConsent = null;
		next?.();
	}

	function closeScope() {
		scopeOpen = false;
		afterConsent = null;
	}

	async function regenerate(messageId: number) {
		if (!thread || regeneratingId !== null) return;
		if (needsConsent(engine)) {
			afterConsent = () => regenerate(messageId);
			scopeOpen = true;
			return;
		}
		regeneratingId = messageId;
		errorMessage = null;
		try {
			const res = await regenerateMessage(thread.id, messageId);
			messages = messages.map((m) => (m.id === messageId ? { ...m, ...res.message } : m));
		} catch (e) {
			errorMessage = e instanceof ApiError ? e.message : '다시 생성에 실패했습니다.';
		} finally {
			regeneratingId = null;
		}
	}

	let inputText = $state('');
	let sending = $state(false);
	let messagesEnd: HTMLDivElement | undefined = $state();

	const lastMsg = $derived(messages[messages.length - 1] ?? null);

	// MetricBreakdown 드릴다운 스택
	let drillStack = $state<DrillTarget[]>([]);
	const drillTop = $derived(drillStack.length > 0 ? drillStack[drillStack.length - 1] : null);

	// 근거 칩 scope는 대화에서 인용한 날짜라 화면 기준일과 다를 수 있다(D1d) — 지원 슬러그면
	// 그 scope 그대로 새 DrillPanel로, 아니면(임의 슬러그) 기존 MetricBreakdown 유지.
	let answerChip = $state<AnswerEvidence | null>(null);

	function openEvidence(ev: AnswerEvidence) {
		if (chipTarget(ev) === 'race') {
			goto(`${base}/today/race`);
			return;
		}
		if (!ev.drill) return;
		answerChip = ev;
		const t: DrillTarget = { slug: ev.metric, scopeType: ev.drill.scope_type, scopeId: ev.drill.scope_id };
		if (t.scopeType === 'daily' && EXPLAIN_SUPPORTED_SLUGS.has(t.slug)) {
			openDrill(t.slug, t.scopeId);
			return;
		}
		drillStack = [...drillStack, t];
	}

	function closeDrill() {
		drillStack = [];
	}

	function handleDrillInput(slug: string) {
		const top = drillStack.length > 0 ? drillStack[drillStack.length - 1] : null;
		drillStack = [
			...drillStack,
			{
				slug,
				scopeType: top?.scopeType ?? 'daily',
				scopeId: top?.scopeId ?? ''
			}
		];
	}

	function scrollToBottom() {
		messagesEnd?.scrollIntoView({ block: 'end' });
	}

	function sendTyped() {
		send(inputText);
	}

	async function send(input: CoachInput) {
		const content = chipLabel(input).trim();
		if (!content || sending || !thread) return;
		if (needsConsent(engine)) {
			afterConsent = () => send(input);
			scopeOpen = true;
			return;
		}

		// 낙관적 사용자 메시지 추가
		const tempUserMsg: ChatMessage = {
			id: Date.now(),
			role: 'user',
			content,
			ai_model: null,
			created_at: new Date().toISOString()
		};
		messages = [...messages, tempUserMsg];
		if (typeof input === 'string') inputText = '';
		sending = true;
		errorMessage = null;

		// 스크롤
		setTimeout(scrollToBottom, 50);

		try {
			const res = await addMessage(thread.id, input);
			messages = [
				...messages,
				{
					...res.message,
					created_at: res.message.created_at ?? new Date().toISOString()
				}
			];
			setTimeout(scrollToBottom, 50);
		} catch (e) {
			errorMessage = e instanceof ApiError ? e.message : '메시지 전송에 실패했습니다.';
		} finally {
			sending = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		// 한글 IME 조합 중 Enter는 글자 확정용 — 전송하면 마지막 글자가 중복·누락된다.
		if (e.isComposing || e.keyCode === 229) return;
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			sendTyped();
		}
	}
</script>

<svelte:head><title>Coach 대화 · RunPulse</title></svelte:head>

{#if !thread}
	<div class="flex flex-col items-center gap-3 px-4 py-20 text-center">
		<p class="text-lg text-fg-secondary">대화를 찾을 수 없습니다</p>
		{#if data.errorMessage}
			<p class="text-xs text-fg-muted">{data.errorMessage}</p>
		{/if}
		<a href="{base}/coach" class="text-sm text-fg-secondary underline">← Coach로</a>
	</div>
{:else}
<DrillPanel scopeType="daily" scopeId={localDateString()} {answerChip}>
	<!-- 헤더 -->
	<div class="flex items-center gap-2 border-b border-border-subtle px-4 py-3">
		<a href="{base}/coach" class="shrink-0 text-fg-muted" aria-label="Coach로">←</a>
		<h1 class="min-w-0 flex-1 truncate text-base font-semibold">{thread.title}</h1>
	</div>

	<!-- 메시지 목록 -->
	<div class="flex min-h-[calc(100dvh-15.5rem)] lg:min-h-[calc(100dvh-11rem)] flex-col gap-3 px-4 py-4">
		{#if messages.length === 0}
			<p class="text-center text-sm text-fg-muted">대화를 시작해 보세요.</p>
		{/if}

		{#each messages as msg (msg.id)}
			{#if msg.role === 'user'}
				<!-- 사용자 말풍선 (오른쪽) -->
				<div class="flex justify-end">
					<div
						class="max-w-[75%] rounded-2xl rounded-br-sm bg-fg-primary px-3 py-2 text-sm text-surface-1"
					>
						{msg.content}
					</div>
				</div>
			{:else}
				<MessageBlock
					{msg}
					regenerating={regeneratingId === msg.id}
					onEvidence={openEvidence}
					onRegenerate={regenerate}
					onShowReason={(m) => (reasonMsg = m)}
				/>
			{/if}
		{/each}

		{#if lastMsg?.role === 'assistant' && !sending && lastMsg.followups?.length}
			<div class="flex flex-wrap gap-2">
				{#each lastMsg.followups as chip (chip.chip_id)}
					<button
						type="button"
						data-testid="followup-chip"
						onclick={() => send(chip)}
						class="rounded-full border border-border-subtle bg-surface-2 px-3 py-1 text-xs text-fg-secondary hover:bg-surface-3"
					>{chip.text}</button>
				{/each}
			</div>
		{/if}

		{#if sending}
			<div class="flex justify-start">
				<div
					class="rounded-2xl rounded-bl-sm border border-border-subtle bg-surface-2 px-3 py-2 text-sm text-fg-muted"
				>
					답변 생성 중…
				</div>
			</div>
		{/if}

		{#if errorMessage}
			<p class="text-center text-xs text-semantic-red">{errorMessage}</p>
		{/if}

		<div bind:this={messagesEnd}></div>
	</div>

	<!-- 입력 바 (하단 탭바 바로 위 고정) -->
	<div class="sticky bottom-14 lg:bottom-0 z-10 flex flex-col gap-1 border-t border-border-subtle bg-surface-1 px-4 py-3">
		<EngineLine {engine} onOpenScope={() => (scopeOpen = true)} />
		<div class="flex items-end gap-2">
			<textarea
				bind:value={inputText}
				onkeydown={handleKeydown}
				placeholder="메시지 입력…"
				rows={1}
				disabled={sending}
				class="flex-1 resize-none rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 text-sm text-fg-primary placeholder:text-fg-muted focus:outline-none disabled:opacity-50"
				style="min-height:2.25rem; max-height:8rem; overflow-y:auto;"
			></textarea>
			<button
				type="button"
				onclick={sendTyped}
				disabled={sending || !inputText.trim()}
				class="rounded-lg bg-fg-primary px-4 py-2 text-sm text-surface-1 disabled:opacity-40"
				aria-label="전송"
			>
				전송
			</button>
		</div>
	</div>

	{#if scopeOpen && engine}
		<ScopeSheet {engine} requireConsent={needsConsent(engine)} onSave={saveConsent} onClose={closeScope} />
	{/if}
	{#if reasonMsg?.engine}
		<EngineSheet engine={reasonMsg.engine} attempted={engine?.selected ?? null} onClose={() => (reasonMsg = null)} />
	{/if}

	<!-- MetricBreakdown 드릴다운 패널 -->
	{#if drillTop}
		<MetricBreakdown
			slug={drillTop.slug}
			scopeType={drillTop.scopeType}
			scopeId={drillTop.scopeId}
			onClose={closeDrill}
			onDrillInput={handleDrillInput}
		/>
	{/if}
</DrillPanel>
{/if}
