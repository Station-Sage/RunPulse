<script lang="ts">
	// Today 하단 신발 교체 한 줄(V2-SHOES Q3) — replace(≥100%)이고 최근 7일 안에 신은 신발만. 보조 정보라 실패 시 조용히 숨긴다.
	import { base } from '$app/paths';
	import { getShoeAlert } from '$lib/api/shoes';
	import Icon from '$lib/components/Icon.svelte';

	let alert = $state<{ id: number; name: string; message: string } | null>(null);
	$effect(() => {
		getShoeAlert()
			.then((r) => (alert = r.alert))
			.catch(() => (alert = null));
	});
</script>

{#if alert}
	<a href="{base}/library/shoes/{alert.id}" data-testid="today-shoe-alert"
		class="flex min-h-11 items-center gap-2 text-sm text-semantic-red hover:underline">
		<Icon name="shoe" class="h-4 w-4" />
		<span>{alert.name}, {alert.message}</span>
	</a>
{/if}
