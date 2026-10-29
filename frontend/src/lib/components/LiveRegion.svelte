<script lang="ts">
	// R3 — 레이아웃에 한 번만 마운트하는 상시 sr-only 공지 영역(polite·assertive). 처음엔 비어 있다.
	import { onMount } from 'svelte';
	import { subscribeAnnounce, type Politeness } from '$lib/a11y/announce';

	let polite = $state('');
	let assertive = $state('');

	onMount(() =>
		subscribeAnnounce((level: Politeness, text: string) => {
			// 같은 문구도 다시 읽히도록 비운 뒤 다음 틱에 채운다
			if (level === 'assertive') assertive = '';
			else polite = '';
			setTimeout(() => {
				if (level === 'assertive') assertive = text;
				else polite = text;
			}, 50);
		})
	);
</script>

<div class="sr-only" data-testid="live-region">
	<div role="status" aria-live="polite" aria-atomic="true">{polite}</div>
	<div role="alert" aria-live="assertive" aria-atomic="true">{assertive}</div>
</div>
