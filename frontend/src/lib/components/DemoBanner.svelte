<script lang="ts">
	// 데모 상단 고정 배너 + 쓰기 차단 시트 (REVIEW03 §2.2). 쓰기 요청이 막히면 시트가 열린다.
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { exitDemo, onDemoWrite } from '$lib/demoMode';

	let sheet = $state(false);
	onMount(() => onDemoWrite(() => (sheet = true)));

	function start() {
		exitDemo();
		window.location.href = `${base}/welcome`;
	}
</script>

<div class="sticky top-0 z-40 flex items-center justify-between gap-2 bg-semantic-amber/20 px-4 py-2 text-xs text-fg-primary" data-testid="demo-banner">
	<span>샘플 러너 "민준"의 합성 데이터예요 · 실제 사람 아님</span>
	<button type="button" class="shrink-0 rounded bg-surface-3 px-2 py-1 font-medium" onclick={start}>내 데이터로 시작</button>
</div>

{#if sheet}
	<div class="fixed inset-0 z-50 flex items-end bg-black/50" role="presentation" onclick={() => (sheet = false)}>
		<div
			class="mx-auto w-full max-w-3xl rounded-t-2xl bg-surface-2 p-5"
			role="dialog"
			aria-modal="true"
			aria-label="데모 안내"
			data-testid="demo-write-sheet"
			tabindex="-1"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.key === 'Escape' && (sheet = false)}
		>
			<p class="font-medium">이건 내 데이터에서 동작해요</p>
			<p class="mt-1 text-sm text-fg-secondary">데모에서는 저장·전송·동기화가 실행되지 않아요.</p>
			<div class="mt-4 flex gap-2">
				<button type="button" class="flex-1 rounded-lg bg-fg-primary px-3 py-2 text-sm font-medium text-surface-1" onclick={start}>시작하기</button>
				<button type="button" class="flex-1 rounded-lg border border-border-subtle px-3 py-2 text-sm" onclick={() => (sheet = false)}>계속 둘러보기</button>
			</div>
		</div>
	</div>
{/if}
