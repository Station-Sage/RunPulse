<script lang="ts">
	import { threadBackHref } from '$lib/activityEvidence';
	// 03e-coach.md 5-B — 대화 스레드: 메시지 목록 + 입력 바.
	// P7-IMPL-COACH-EVIDENCE-UI: 근거 칩(EvidenceQuote) + MetricBreakdown 드릴다운 + 입력창 하단 도킹.
	import type { ThreadPageData } from './+page';
	import {
		addMessage, cancelMessage, newClientMsgId, putConsent, regenerateMessage, type ConsentInput
	} from '$lib/api/coach';
	import { ApiError } from '$lib/api/client';
	import { base } from '$app/paths';
	import type { AnswerEvidence, ChatMessage, CoachEngine } from '$lib/types';
	import { goto } from '$app/navigation';
	import MessageBlock from '$lib/components/coach/MessageBlock.svelte';
	import ChatComposer from '$lib/components/coach/ChatComposer.svelte';
	import ScopeSheet from '$lib/components/coach/ScopeSheet.svelte';
	import EngineSheet from '$lib/components/coach/EngineSheet.svelte';
	import MetricBreakdown from '$lib/components/MetricBreakdown.svelte';
	import DrillPanel from '$lib/components/DrillPanel.svelte';
	import { needsConsent } from '$lib/coachEngine';
	import { CoachLive } from '$lib/coachLive.svelte';
	import { isPendingStatus } from '$lib/coachStream';
	import { onDestroy, onMount } from 'svelte';
	import type { DrillTarget } from '$lib/evidence';
	import { chipTarget } from '$lib/answerEvidence';
	import { inputText as chipLabel, type CoachInput } from '$lib/coachSuggestions';
	import { EXPLAIN_SUPPORTED_SLUGS } from '$lib/api/metrics';
	import { openDrill } from '$lib/drillStack';
	import { localDateString } from '$lib/asOf';

	let { data }: { data: ThreadPageData } = $props();

	const thread = $derived(data.detail?.thread ?? null);
	const back = $derived(threadBackHref(thread?.context, base));
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

	const closeScope = () => ((scopeOpen = false), (afterConsent = null));

	const live = new CoachLive((m) => {
		messages = messages.map((x) => (x.id === m.id ? { ...x, ...m } : x));
		setTimeout(scrollToBottom, 50);
	});
	onMount(() => {
		for (const m of messages) if (m.role === 'assistant' && isPendingStatus(m.status)) live.watch(m.id);
	});
	onDestroy(() => live.stopAll());

	async function regenerate(messageId: number, mode: 'ai' | 'rule' = 'ai') {
		if (regeneratingId !== null) return;
		if (mode === 'ai' && needsConsent(engine)) {
			afterConsent = () => regenerate(messageId, mode);
			scopeOpen = true;
			return;
		}
		regeneratingId = messageId;
		errorMessage = null;
		try {
			const res = await regenerateMessage(messageId, mode);
			live.stop(messageId);
			messages = [...messages.filter((m) => m.id !== messageId), res.message];
			live.watch(res.message.id);
			setTimeout(scrollToBottom, 50);
		} catch (e) {
			errorMessage = e instanceof ApiError ? e.message : '다시 생성에 실패했습니다.';
		} finally {
			regeneratingId = null;
		}
	}

	async function cancel(messageId: number) {
		try {
			await cancelMessage(messageId);
		} catch (e) {
			errorMessage = e instanceof ApiError ? e.message : '중단하지 못했어요.';
		}
	}

	let inputText = $state('');
	let sending = $state(false);
	let messagesEnd: HTMLDivElement | undefined = $state();

	const lastMsg = $derived(messages[messages.length - 1] ?? null);

	// MetricBreakdown 드릴다운 스택
	let drillStack = $state<DrillTarget[]>([]);
	const drillTop = $derived(drillStack.length > 0 ? drillStack[drillStack.length - 1] : null);

	// 근거 칩 scope는 인용 날짜라 화면 기준일과 다를 수 있다(D1d) — 지원 슬러그는 새 DrillPanel, 아니면 MetricBreakdown.
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

	const closeDrill = () => (drillStack = []);

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

	// 아직 서버가 받지 못한 사용자 메시지 — 낙관적으로 70% 투명하게 보이고, 실패하면 같은 client_msg_id로 재시도한다.
	interface Outbox {
		input: CoachInput;
		content: string;
		clientMsgId: string;
		failed: boolean;
	}
	let outbox = $state<Outbox | null>(null);
	const busy = $derived(outbox !== null && !outbox.failed);
	const answering = $derived(
		Object.keys(live.entries).length > 0 || (lastMsg?.role === 'assistant' && isPendingStatus(lastMsg.status))
	);

	const sendTyped = () => {
		const text = inputText;
		inputText = '';
		send(text);
	};

	async function send(input: CoachInput, retry?: Outbox) {
		const content = chipLabel(input).trim();
		if (!content || busy || !thread) return;
		if (needsConsent(engine)) {
			if (typeof input === 'string') inputText = input;
			afterConsent = () => send(input);
			scopeOpen = true;
			return;
		}
		outbox = { input, content, clientMsgId: retry?.clientMsgId ?? newClientMsgId(), failed: false };
		errorMessage = null;
		setTimeout(scrollToBottom, 50);

		try {
			const res = await addMessage(thread.id, input, outbox.clientMsgId);
			outbox = null;
			const known = new Set(messages.map((m) => m.id));
			messages = [...messages, ...[res.user_message, res.assistant_message].filter((m) => !known.has(m.id))];
			if (isPendingStatus(res.assistant_message.status)) live.watch(res.assistant_message.id);
			setTimeout(scrollToBottom, 50);
		} catch {
			if (outbox) outbox.failed = true;
		}
	}

	function editFailed() {
		if (!outbox) return;
		if (typeof outbox.input === 'string') inputText = outbox.content;
		outbox = null;
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
		<a href={back.href} class="shrink-0 text-fg-muted" aria-label={back.label} data-testid="thread-back">←</a>
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
					live={live.entries[msg.id]}
					onRegenerate={(id) => regenerate(id)}
					onCancel={cancel}
					onKeepWaiting={(id) => live.keepWaiting(id)}
					onRuleAnswer={(id) => regenerate(id, 'rule')}
					onShowReason={(m) => (reasonMsg = m)}
				/>
			{/if}
		{/each}

		{#if outbox}
			<div class="flex flex-col items-end gap-1">
				<div
					class="max-w-[75%] rounded-2xl rounded-br-sm bg-fg-primary px-3 py-2 text-sm text-surface-1"
					class:opacity-70={!outbox.failed}
					data-testid="outbox-bubble"
				>
					{outbox.content}
				</div>
				{#if outbox.failed}
					<p class="text-xs text-semantic-red" data-testid="send-failed">
						⚠ 전송 실패 ·
						<button type="button" class="underline" data-testid="retry-send" onclick={() => outbox && send(outbox.input, outbox)}>다시 보내기</button> ·
						<button type="button" class="underline" data-testid="edit-send" onclick={editFailed}>수정</button>
					</p>
				{/if}
			</div>
		{/if}

		{#if lastMsg?.role === 'assistant' && !answering && !outbox && lastMsg.followups?.length}
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

		{#if errorMessage}
			<p class="text-center text-xs text-semantic-red">{errorMessage}</p>
		{/if}

		<div bind:this={messagesEnd}></div>
	</div>

	<ChatComposer {engine} bind:value={inputText} {busy} onSend={sendTyped} onOpenScope={() => (scopeOpen = true)} />

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
