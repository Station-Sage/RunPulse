<script lang="ts">
	// Garmin 연결 시트(V2-GARMIN-CONNECT §3.6) — ① 이메일·비밀번호 → ② MFA 코드 → ③ 완료, 접힘 "고급"에 토큰 붙여넣기.
	// mfa_ticket 은 이 컴포넌트 메모리에만 둔다(URL·저장소 금지). 비밀번호는 요청 직후 비운다.
	import { onDestroy } from 'svelte';
	import { say } from '$lib/a11y/say';
	import { garminLogin, garminMfa, garminMfaCancel, garminToken, LOCAL_KIT_ENV_URL, LOCAL_KIT_SCRIPT_URL } from '$lib/api/garmin';
	import { formatRemaining, garminErrorText, isValidCode, last30Range, stepAfter, type GarminMode, type GarminStep } from '$lib/garminConnect';
	import { runRangeTrigger, syncStore } from '$lib/syncStore.svelte';
	import Icon from '../Icon.svelte';

	let { email: initialEmail = '', onConnected, onClose }: {
		email?: string;
		onConnected?: () => void;
		onClose?: () => void;
	} = $props();

	// svelte-ignore state_referenced_locally
	let email = $state(initialEmail);
	let password = $state('');
	let code = $state('');
	let tokenJson = $state('');
	let step = $state<GarminStep>('credentials');
	let ticket = '';
	let deadline = 0;
	let remaining = $state(0);
	let busy = $state(false);
	let error = $state('');
	let synced = $state(false);
	let timer: ReturnType<typeof setInterval> | undefined;
	let codeEl = $state<HTMLInputElement | null>(null);
	$effect(() => {
		if (step === 'mfa') codeEl?.focus();
	});

	function stopTimer() {
		if (timer) clearInterval(timer);
		timer = undefined;
	}
	onDestroy(stopTimer);

	function toCredentials(msg = '') {
		stopTimer();
		ticket = '';
		code = '';
		step = 'credentials';
		error = msg;
	}

	function startTimer(sec: number) {
		deadline = Date.now() + sec * 1000;
		remaining = sec;
		stopTimer();
		timer = setInterval(() => {
			remaining = Math.max(0, Math.round((deadline - Date.now()) / 1000));
			if (remaining <= 0) toCredentials('시간이 지났어요. 다시 로그인해 주세요');
		}, 1000);
	}

	function finish() {
		stopTimer();
		ticket = '';
		step = 'done';
		error = '';
		onConnected?.();
	}

	async function run(mode: GarminMode, fn: () => Promise<void>) {
		busy = true;
		error = '';
		try {
			await fn();
		} catch (e) {
			const v = garminErrorText(e, mode);
			if (v.clearCode) code = '';
			if (v.resetTo === 'credentials') toCredentials(v.text);
			else error = v.text;
		} finally {
			busy = false;
		}
	}

	const login = () =>
		run('login', async () => {
			const pw = password;
			password = '';
			const r = await garminLogin(email.trim(), pw);
			if (r.status === 'needs_mfa') {
				ticket = r.mfa_ticket;
				code = '';
				step = 'mfa';
				startTimer(r.expires_in);
			} else if (stepAfter(r) === 'done') finish();
		});

	const submitCode = () => run('mfa', async () => { await garminMfa(ticket, code.trim()); finish(); });

	const restart = () =>
		run('mfa', async () => {
			toCredentials();
			await garminMfaCancel();
		});

	const pasteToken = () =>
		run('token', async () => {
			await garminToken(tokenJson);
			tokenJson = '';
			finish();
		});

	async function syncRecent() {
		const { from, to } = last30Range();
		await runRangeTrigger('garmin', from, to);
		synced = true;
	}

	const input = 'mt-1 w-full rounded border border-border-subtle bg-surface-1 p-2 text-sm';
	const primary = 'min-h-11 rounded-lg bg-fg-primary px-4 py-2 text-sm text-surface-1 disabled:opacity-50';
</script>

<div class="flex flex-col gap-3 rounded-lg border border-border-subtle bg-surface-1 p-4" data-testid="garmin-connect-sheet" data-step={step}>
	<div class="flex items-center justify-between">
		<p class="text-sm font-medium text-fg-primary">Garmin 연결</p>
		{#if onClose}<button type="button" onclick={onClose} class="h-11 px-2 text-xs text-fg-muted hover:text-fg-primary">닫기</button>{/if}
	</div>

	{#if step === 'credentials'}
		<form class="flex flex-col gap-2" onsubmit={(e) => { e.preventDefault(); login(); }}>
			<label class="text-xs text-fg-secondary">Garmin 이메일
				<input class={input} type="email" bind:value={email} autocomplete="username" required />
			</label>
			<label class="text-xs text-fg-secondary">비밀번호
				<input class={input} type="password" bind:value={password} autocomplete="current-password" required />
			</label>
			<p class="text-xs text-fg-muted">비밀번호는 저장하지 않아요. 로그인 토큰만 보관해요.</p>
			<button type="submit" class={primary} disabled={busy || !email.trim() || !password}>{busy ? '확인 중…' : '로그인'}</button>
		</form>
	{:else if step === 'mfa'}
		<form class="flex flex-col gap-2" onsubmit={(e) => { e.preventDefault(); submitCode(); }}>
			<p class="text-xs text-fg-secondary">Garmin 앱이나 이메일로 받은 인증 코드를 입력해 주세요.</p>
			<label class="text-xs text-fg-secondary">인증 코드
				<input class="{input} tracking-widest" bind:value={code} bind:this={codeEl} inputmode="numeric" autocomplete="one-time-code" maxlength="8" />
			</label>
			<p class="text-xs text-fg-muted" aria-live="off">남은 시간 {formatRemaining(remaining)}</p>
			<div class="flex items-center gap-3">
				<button type="submit" class={primary} disabled={busy || !isValidCode(code)}>{busy ? '확인 중…' : '인증'}</button>
				<button type="button" class="min-h-11 text-xs underline" disabled={busy} onclick={restart}>처음부터</button>
			</div>
		</form>
	{:else}
		<div class="flex flex-col gap-2">
			<p class="flex items-center gap-2 text-sm text-fg-primary"><Icon name="check" class="h-4 w-4 text-semantic-teal" />연결됐어요</p>
			{#if synced}
				<p class="text-xs text-fg-secondary">{syncStore.notice ?? '동기화를 시작했어요'}</p>
			{:else}
				<button type="button" class={primary} disabled={syncStore.triggering} onclick={syncRecent}>최근 30일 가져오기</button>
			{/if}
		</div>
	{/if}

	{#if error}<p class="text-xs text-semantic-red" use:say={{ text: error, level: 'assertive' }}>{error}</p>{/if}

	{#if step === 'credentials'}
		<details class="text-xs text-fg-secondary">
			<summary class="flex min-h-11 cursor-pointer items-center">고급: 토큰 붙여넣기·로컬 동기화</summary>
			<form class="mt-2 flex flex-col gap-2" onsubmit={(e) => { e.preventDefault(); pasteToken(); }}>
				<label>PC에서 발급한 garmin_tokens.json 내용
					<textarea class="{input} font-mono" rows="4" bind:value={tokenJson} autocomplete="off" spellcheck="false"></textarea>
				</label>
				<button type="submit" class={primary} disabled={busy || !tokenJson.trim()}>토큰으로 연결</button>
			</form>
			<p class="mt-3">서버 로그인이 막히면 PC에서 동기화 스크립트를 실행할 수 있어요(Python 3.12).</p>
			<div class="mt-1 flex gap-3">
				<a class="inline-flex min-h-11 items-center underline" href={LOCAL_KIT_SCRIPT_URL} download>스크립트 받기</a>
				<a class="inline-flex min-h-11 items-center underline" href={LOCAL_KIT_ENV_URL} download>.env 받기</a>
			</div>
		</details>
	{/if}
</div>
