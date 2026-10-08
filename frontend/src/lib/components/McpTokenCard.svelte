<script lang="ts">
	import { getMcpTokens, issueMcpToken, revokeMcpToken, type McpTokenList } from '$lib/api/mcpTokens';
	import { expiryText, lastUsedText, mcpEndpoint } from '$lib/mcpTokens';

	let { initial }: { initial: McpTokenList | null } = $props();
	let list = $state<McpTokenList | null>(initial);
	let label = $state('');
	let busy = $state(false);
	let message = $state('');
	let fresh = $state<string | null>(null);
	let confirmId = $state<string | null>(null);
	const endpoint = $derived(mcpEndpoint(typeof location === 'undefined' ? '' : location.origin));

	async function issue() {
		if (!label.trim()) return;
		busy = true;
		message = '';
		try {
			const r = await issueMcpToken(label.trim());
			fresh = r.token;
			label = '';
			list = await getMcpTokens();
		} catch (e) {
			message = e instanceof Error ? e.message : '토큰을 만들지 못했어요';
		} finally {
			busy = false;
		}
	}

	async function revoke(id: string) {
		busy = true;
		try {
			await revokeMcpToken(id);
			list = await getMcpTokens();
			message = '토큰을 폐기했어요. 바로 사용할 수 없게 돼요';
		} catch (e) {
			message = e instanceof Error ? e.message : '폐기하지 못했어요';
		} finally {
			busy = false;
			confirmId = null;
		}
	}

	async function copy(text: string) {
		try {
			await navigator.clipboard.writeText(text);
			message = '복사했어요';
		} catch {
			message = '복사하지 못했어요. 직접 선택해 복사해 주세요';
		}
	}
</script>

<section aria-label="외부 AI 연결" class="flex flex-col gap-2 rounded-lg border border-border-subtle bg-surface-2 p-3">
	<h2 class="text-sm text-fg-primary">외부 AI 연결</h2>
	{#if list === null}
		<p class="text-xs text-fg-muted">연결 상태를 불러오지 못했어요</p>
	{:else}
		<p class="text-xs text-fg-secondary">
			Claude·Genspark 같은 외부 AI가 내 러닝 기록을 읽기 전용으로 조회할 수 있어요. 토큰을 아는 사람은 누구나 조회할 수 있으니 공유하지 마세요.
		</p>
		{#if !list.enabled}
			<p class="text-xs text-semantic-amber" role="status">아직 서버에서 외부 연결이 꺼져 있어요. 토큰은 미리 만들 수 있어요.</p>
		{/if}
		<div class="flex gap-2">
			<input bind:value={label} maxlength="40" placeholder="이름 (예: Genspark)" aria-label="토큰 이름"
				class="min-w-0 flex-1 rounded border border-border-subtle bg-surface-1 px-2 py-1 text-xs text-fg-primary" />
			<button type="button" disabled={busy || !label.trim() || list.tokens.length >= list.max_active} onclick={issue}
				class="rounded border border-border-subtle bg-surface-3 px-3 py-1.5 text-xs text-fg-primary disabled:opacity-60">토큰 만들기</button>
		</div>
		<p class="text-xs text-fg-muted">활성 토큰 {list.tokens.length}/{list.max_active} · 유효 {list.default_days}일</p>
		{#if fresh}
			<div class="flex flex-col gap-1 rounded border border-border-subtle bg-surface-1 p-2 text-xs" role="status">
				<p class="text-fg-primary">지금만 볼 수 있어요. 복사해 AI 앱에 붙여넣으세요.</p>
				<input readonly value={fresh} aria-label="새 토큰" onfocus={(e) => e.currentTarget.select()}
					class="rounded border border-border-subtle bg-surface-2 px-2 py-1 text-fg-secondary" />
				<div class="flex gap-2">
					<button type="button" onclick={() => copy(fresh!)} class="rounded border border-border-subtle bg-surface-3 px-3 py-1.5 text-fg-primary">토큰 복사</button>
					<button type="button" onclick={() => (fresh = null)} class="rounded border border-border-subtle px-3 py-1.5 text-fg-secondary">닫기</button>
				</div>
			</div>
		{/if}
		{#each list.tokens as t (t.token_id)}
			<div class="flex items-center justify-between gap-2 rounded border border-border-subtle bg-surface-1 p-2 text-xs">
				<div class="flex min-w-0 flex-col">
					<span class="truncate text-fg-primary">{t.label} · ••••{t.last4}</span>
					<span class="text-fg-muted">{expiryText(t)} · {lastUsedText(t)}</span>
				</div>
				{#if confirmId === t.token_id}
					<div role="alertdialog" aria-label="폐기 확인" class="flex gap-2">
						<button type="button" disabled={busy} onclick={() => revoke(t.token_id)} class="text-semantic-red underline disabled:opacity-60">폐기</button>
						<button type="button" onclick={() => (confirmId = null)} class="text-fg-secondary underline">취소</button>
					</div>
				{:else}
					<button type="button" onclick={() => (confirmId = t.token_id)} class="text-fg-secondary underline">폐기</button>
				{/if}
			</div>
		{/each}
		<details class="text-xs text-fg-secondary">
			<summary class="cursor-pointer">연결 방법</summary>
			<p class="mt-1">서버 주소: <code>{endpoint}</code></p>
			<p>인증: <code>Authorization: Bearer 토큰</code></p>
			<p>Claude Code: <code>claude mcp add --transport http runpulse {endpoint} --header "Authorization: Bearer 토큰"</code></p>
			<button type="button" class="mt-1 underline" onclick={() => copy(endpoint)}>서버 주소 복사</button>
		</details>
	{/if}
	{#if message}<p class="text-xs text-fg-secondary" role="status">{message}</p>{/if}
</section>
