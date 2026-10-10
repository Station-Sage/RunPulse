<script lang="ts">
	// S0 랜딩 — DESIGN-P7-REVIEW03 §2.1. 정적 화면: API 호출·로딩 상태 없음. 가짜 후기·통계 금지.
	import { base } from '$app/paths';

	const INVITE_HREF = 'mailto:pansong.us@gmail.com?subject=RunPulse%20초대%20요청';
	const proofs = [
		{ title: '같은 달리기, 다른 숫자', body: 'Garmin 10.02km, Strava 10.05km. 어느 쪽을 쓰는지 근거와 함께 보여줘요.', to: '/library' },
		{ title: 'CIRS 62, 계산식까지', body: '점수만이 아니라 계산식과 입력값을 눌러서 확인해요.', to: '/library/metrics/cirs' },
		{ title: '"오늘은 쉬어가요"의 근거 3개', body: '권고 문장마다 근거를 칩으로 연결해요.', to: '/today' }
	];
	const demoHref = (to = '/today') => `${base}/demo?to=${to}`;
</script>

<svelte:head><title>RunPulse</title></svelte:head>

<main class="mx-auto flex max-w-2xl flex-col gap-8 px-4 py-10" data-testid="landing">
	<header class="flex flex-col gap-4">
		<p class="text-xs uppercase tracking-wide text-fg-muted">RunPulse</p>
		<h1 class="text-2xl font-semibold leading-snug text-fg-primary">
			Garmin·Strava·Intervals·Runalyze를 오가며 맞추던 숫자, 한 화면에서 근거까지.
		</h1>
		<div class="flex flex-wrap gap-2">
			<a href={demoHref()} class="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white" data-testid="landing-demo">샘플 러너로 둘러보기</a>
			<a href={INVITE_HREF} class="rounded-lg border border-border-subtle px-4 py-2 text-sm text-fg-primary" data-testid="landing-invite">내 데이터로 시작 · 초대 요청</a>
		</div>
		<p class="text-xs text-fg-muted">지금은 초대받은 분만 시작할 수 있어요.</p>
	</header>

	<section class="grid gap-3 sm:grid-cols-3">
		{#each proofs as p}
			<a href={demoHref(p.to)} class="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-2 p-3 hover:bg-surface-3">
				<span class="text-sm font-medium text-fg-primary">{p.title}</span>
				<span class="text-xs text-fg-secondary">{p.body}</span>
			</a>
		{/each}
	</section>

	<section class="flex flex-col gap-1 text-sm text-fg-secondary">
		<p class="font-medium text-fg-primary">내 데이터는 내 것이에요</p>
		<p>계정마다 저장소가 분리되고, 언제든 내보낼 수 있고, AI에는 내가 허용한 범위만 보내요.</p>
	</section>

	<section class="flex flex-col gap-1 text-sm text-fg-secondary">
		<p class="font-medium text-fg-primary">트래커가 없어도 괜찮아요</p>
		<p>직접 기록해도 시작할 수 있어요. 데이터가 쌓일수록 볼 수 있는 지표가 늘어나요.</p>
	</section>
</main>
