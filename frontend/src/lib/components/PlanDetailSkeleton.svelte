<script lang="ts">
	// P-25 — 플랜 상세로 이동 중(로더 대기) 보이는 자리 표시. 실제 화면의 머리·요약 카드·주 목록 자리를 흉내 낸다.
	import Skeleton from './Skeleton.svelte';
</script>

<div class="flex flex-col" aria-busy="true" data-testid="plan-detail-skeleton">
	<span class="sr-only">플랜을 불러오는 중</span>
	<div class="flex flex-col gap-2 border-b border-border-subtle px-4 py-4">
		<Skeleton class="w-20" />
		<Skeleton class="h-5 w-48" />
		<Skeleton class="w-32" />
	</div>
	<div class="px-4 py-4"><Skeleton kind="chart" /></div>
	<div class="flex flex-col gap-3 px-4 pb-6">
		{#each [0, 1, 2] as i (i)}
			<Skeleton kind="chart" />
		{/each}
	</div>
</div>
