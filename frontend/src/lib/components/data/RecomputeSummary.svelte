<script lang="ts">
	import { getJob, type RecomputeJob } from '$lib/api/data';
	import { formatDelta, formatMetric, progressPct } from '$lib/recompute';

	let { jobId, onDone }: { jobId: string; onDone?: () => void } = $props();
	let job = $state<RecomputeJob | null>(null);
	let failed = $state(false);

	$effect(() => {
		const id = jobId;
		let stop = false;
		let timer: ReturnType<typeof setTimeout>;
		async function poll() {
			try {
				job = await getJob(id);
				failed = false;
			} catch {
				failed = true;
			}
			if (stop) return;
			if (job && (job.state === 'done' || job.state === 'failed')) {
				if (job.state === 'done') onDone?.();
				return;
			}
			timer = setTimeout(poll, 1500);
		}
		poll();
		return () => {
			stop = true;
			clearTimeout(timer);
		};
	});
</script>

<section aria-label="재계산 결과" class="rounded-lg border border-border-subtle bg-surface-2 p-3 text-xs">
	{#if !job}
		<p class="text-fg-muted" role="status">{failed ? '진행 상황을 불러오지 못했어요' : '재계산을 준비하고 있어요'}</p>
	{:else if job.state === 'failed'}
		<p class="text-semantic-red" role="status">재계산에 실패했어요{job.error ? ` — ${job.error}` : ''}</p>
	{:else if job.state !== 'done'}
		<p class="text-fg-secondary" role="status">재계산 중… {progressPct(job)}% ({job.progress.done}/{job.progress.total}일)</p>
		<progress class="mt-1 w-full" max="100" value={progressPct(job)}></progress>
	{:else if job.result}
		<h3 class="font-semibold text-fg-primary">재계산 완료 · {job.result.changed_days}일</h3>
		<table class="mt-2 w-full">
			<thead class="text-fg-muted"><tr><th class="text-left">지표</th><th class="text-right">이전</th><th class="text-right">이후</th><th class="text-right">변화</th></tr></thead>
			<tbody>
				{#each job.result.before_after as r (r.slug)}
					<tr class="text-fg-secondary">
						<td>{r.label}</td>
						<td class="text-right">{formatMetric(r.slug, r.before)}</td>
						<td class="text-right text-fg-primary">{formatMetric(r.slug, r.after)}</td>
						<td class="text-right">{formatDelta(r)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</section>
