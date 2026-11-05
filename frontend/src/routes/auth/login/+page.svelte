<script lang="ts">
	// 로그인 또는 가입 — CF Access(GitHub·Google·이메일 코드)로 보낸다. 가입 여부는 로그인 뒤 서버가 판단한다.
	import { page } from '$app/state';
	import { base } from '$app/paths';
	import { loginHref } from '$lib/auth/guard';

	const next = $derived(page.url.searchParams.get('next') ?? `${base}/today`);
</script>

<svelte:head><title>로그인 · RunPulse</title></svelte:head>

<main class="mx-auto flex max-w-md flex-col gap-4 px-4 py-12" data-testid="auth-login">
	<h1 class="text-xl font-semibold text-fg-primary">로그인 또는 가입</h1>
	<p class="text-sm text-fg-secondary">GitHub, Google, 이메일 코드 중 편한 방법으로 확인해요. 처음이면 다음 화면에서 초대코드를 입력해요.</p>
	<a href={loginHref(next)} data-sveltekit-reload class="inline-flex min-h-11 items-center justify-center rounded-lg bg-accent px-4 py-2 text-sm font-medium text-fg-on-accent" data-testid="auth-login-go">로그인 또는 가입</a>
	<a href="{base}/demo" class="text-center text-sm text-fg-secondary underline">샘플 러너로 둘러보기</a>
</main>
