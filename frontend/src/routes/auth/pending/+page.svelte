<script lang="ts">
	// 가입 대기 — 초대코드로 계정을 활성화한다.
	import { onMount, tick } from 'svelte';
	import { afterNavigate } from '$app/navigation';
	import { base } from '$app/paths';
	import { apiFetch, ApiError } from '$lib/api/client';
	import { inviteErrorMessage } from '$lib/auth/guard';
	import { loadAuthSession } from '$lib/auth/session';
	import TextField from '$lib/components/ui/TextField.svelte';

	let code = $state('');
	let busy = $state(false);
	let error = $state<string | null>(null);
	let email = $state<string | null>(null);
	let heading: HTMLHeadingElement | undefined = $state();

	afterNavigate(() => setTimeout(() => heading?.focus(), 0));

	onMount(async () => {
		heading?.focus();
		email = (await loadAuthSession())?.email ?? null;
	});

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		if (busy || !code.trim()) return;
		busy = true;
		error = null;
		try {
			await apiFetch('/auth/invite', { method: 'POST', body: JSON.stringify({ code: code.trim() }) });
			await loadAuthSession(true);
			location.assign(`${base}/welcome`);
		} catch (err) {
			error = err instanceof ApiError ? inviteErrorMessage(err.status, err.code) : inviteErrorMessage(0, '');
			busy = false;
			await tick();
		}
	}
</script>

<svelte:head><title>초대코드 · RunPulse</title></svelte:head>

<main class="mx-auto flex max-w-md flex-col gap-4 px-4 py-12" data-testid="auth-pending">
	<h1 bind:this={heading} tabindex="-1" class="text-xl font-semibold text-fg-primary outline-none">초대코드를 입력해 주세요</h1>
	<p class="text-sm text-fg-secondary">{email ? `${email} 계정으로 확인됐어요. ` : ''}초대코드로 가입을 마칠 수 있어요.</p>
	<form onsubmit={submit} class="flex flex-col gap-3">
		<TextField label="초대코드" bind:value={code} autocomplete="off" autocapitalize="off" spellcheck={false} class="w-full rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 text-sm" />
		<p aria-live="polite" class="min-h-5 text-sm text-semantic-red" data-testid="auth-pending-error">{error ?? ''}</p>
		<button type="submit" disabled={busy || !code.trim()} class="min-h-11 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-fg-on-accent disabled:opacity-50">{busy ? '확인 중…' : '가입 완료'}</button>
	</form>
	<form method="POST" action="/auth/logout">
		<button type="submit" class="min-h-11 text-sm text-fg-secondary underline">다른 계정으로 로그인</button>
	</form>
</main>
