<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { base } from '$app/paths';
	import ErrorState from '$lib/components/ErrorState.svelte';
</script>

<svelte:head><title>샘플 러너 · RunPulse</title></svelte:head>

<div class="px-4 py-10" data-testid="demo-error">
	<ErrorState message="데모를 불러오지 못했어요" onRetry={() => invalidateAll()} />
	<p class="mt-4 text-center text-sm"><a class="text-fg-secondary underline" href="{base}/">처음 화면으로</a></p>
</div>
