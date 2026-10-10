<script lang="ts">
	// 0단계 — 신규 계정 1회 안내(DESIGN-P7-REVIEW03 §2.3).
	let { onStart }: { onStart: () => void } = $props();
</script>

<div class="flex flex-col gap-3">
	<h1 class="text-lg font-semibold text-fg-primary">반가워요</h1>
	<p class="text-sm text-fg-secondary">데이터는 이 계정 전용 공간에 따로 보관돼요. 기기를 연결하고 지난 기록을 가져오면 오늘 상태 분석이 시작됩니다. 몇 분이면 끝나요.</p>
	<button type="button" class="rounded-lg bg-fg-primary px-4 py-2 text-sm text-surface-1" onclick={onStart}>시작</button>
</div>
