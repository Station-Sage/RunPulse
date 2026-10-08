<script lang="ts">
	import {
		getImportJob, getImports, previewImport, startImport, startRecompute,
		type ImportItem, type ImportPreview, type ImportSource
	} from '$lib/api/data';
	import { canCommit, kindLabel, periodText, previewLines } from '$lib/importFlow';
	import type { ImportPageData } from './+page';

	let { data }: { data: ImportPageData } = $props();
	let history = $state<ImportItem[] | null>(data.history);
	let source = $state<ImportSource>('strava');
	let files = $state<File[]>([]);
	let preview = $state<ImportPreview | null>(null);
	let job = $state<ImportItem | null>(null);
	let busy = $state(false);
	let message = $state('');
	let recomputeStarted = $state(false);

	const step = $derived(job ? (job.state === 'done' || job.state === 'failed' ? 4 : 3) : preview ? 2 : 1);

	function pick(e: Event) {
		files = Array.from((e.currentTarget as HTMLInputElement).files ?? []);
		preview = null;
		message = '';
	}

	async function check() {
		busy = true;
		message = '';
		try {
			preview = await previewImport(files, source);
		} catch (e) {
			message = e instanceof Error ? e.message : '파일을 확인하지 못했어요';
		} finally {
			busy = false;
		}
	}

	async function run() {
		if (!preview) return;
		busy = true;
		message = '';
		try {
			const { job_id } = await startImport(preview.upload_id, source);
			job = await getImportJob(job_id);
		} catch (e) {
			message = e instanceof Error ? e.message : '가져오기를 시작하지 못했어요';
		} finally {
			busy = false;
		}
	}

	$effect(() => {
		const id = job?.id;
		if (!id || job?.state === 'done' || job?.state === 'failed') return;
		const t = setInterval(async () => {
			try {
				job = await getImportJob(id);
				if (job.state === 'done' || job.state === 'failed') history = await getImports();
			} catch {
				/* 다음 폴링에서 다시 시도 */
			}
		}, 1500);
		return () => clearInterval(t);
	});

	async function recompute() {
		try {
			await startRecompute('90d');
			recomputeStarted = true;
		} catch (e) {
			message = e instanceof Error ? e.message : '재계산을 시작하지 못했어요';
		}
	}

	function again() {
		files = [];
		preview = null;
		job = null;
		recomputeStarted = false;
		message = '';
	}
</script>

<svelte:head><title>가져오기 · RunPulse</title></svelte:head>

<div class="flex flex-col gap-3 px-4 py-4">
	<ol class="flex gap-2 text-xs text-fg-muted" aria-label="진행 단계">
		{#each ['파일 선택', '미리보기', '가져오는 중', '결과'] as label, i (label)}
			<li class={step === i + 1 ? 'text-fg-primary' : ''} aria-current={step === i + 1 ? 'step' : undefined}>{i + 1}. {label}</li>
		{/each}
	</ol>

	{#if step === 1 || step === 2}
		<fieldset class="flex gap-3 text-xs text-fg-secondary">
			<legend class="mb-1">어느 소스의 파일인가요?</legend>
			<label><input type="radio" bind:group={source} value="strava" onchange={() => (preview = null)} /> Strava</label>
			<label><input type="radio" bind:group={source} value="garmin" onchange={() => (preview = null)} /> Garmin</label>
		</fieldset>
		<label class="flex flex-col gap-1 text-xs text-fg-secondary">
			Strava 내보내기 zip, 활동 CSV, FIT/GPX/TCX 파일(여러 개 가능)
			<input type="file" multiple accept=".zip,.csv,.fit,.gpx,.tcx,.gz" onchange={pick} class="text-fg-primary" />
		</label>
		<button
			type="button"
			disabled={busy || files.length === 0}
			onclick={check}
			class="rounded-lg border border-border-subtle bg-surface-2 p-3 text-sm text-fg-primary hover:bg-surface-3 disabled:opacity-60"
		>{busy && !preview ? '확인하는 중…' : '파일 확인하기'}</button>
	{/if}

	{#if step === 2 && preview}
		<section aria-label="미리보기" class="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-2 p-3">
			<h2 class="text-sm text-fg-primary">{kindLabel(preview.kind)}</h2>
			{#each previewLines(preview) as line (line)}<p class="text-xs text-fg-secondary">{line}</p>{/each}
			<p class="text-xs text-fg-muted">아직 내 데이터에는 아무것도 들어가지 않았어요.</p>
		</section>
		<button
			type="button"
			disabled={busy || !canCommit(preview)}
			onclick={run}
			class="rounded-lg border border-border-subtle bg-surface-3 p-3 text-sm text-fg-primary disabled:opacity-60"
		>{busy ? '시작하는 중…' : '가져오기'}</button>
	{/if}

	{#if step === 3}
		<p class="text-sm text-fg-secondary" role="status">가져오는 중이에요. 이 화면을 닫아도 계속돼요.</p>
	{/if}

	{#if step === 4 && job}
		<section aria-label="결과" class="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-2 p-3">
			{#if job.state === 'failed'}
				<p class="text-sm text-semantic-red">가져오지 못했어요{job.error ? ` — ${job.error}` : ''}</p>
			{:else if job.result}
				<h2 class="text-sm text-fg-primary">가져오기를 마쳤어요</h2>
				<p class="text-xs text-fg-secondary">새 활동 {job.result.new}건 · 보강 {job.result.enriched}건 · 건너뜀 {job.result.skipped}건 · 오류 {job.result.errors}건</p>
				<p class="text-xs text-fg-secondary">기간 {periodText(job.result.period)}</p>
				{#if job.result.suggest_recompute}
					<button
						type="button"
						disabled={recomputeStarted}
						onclick={recompute}
						class="mt-2 rounded border border-border-subtle bg-surface-3 px-3 py-2 text-xs text-fg-primary disabled:opacity-60"
					>{recomputeStarted ? '재계산을 시작했어요' : '최근 90일 지표 다시 계산하기'}</button>
				{/if}
			{/if}
		</section>
		<button type="button" onclick={again} class="text-xs text-fg-primary underline">다른 파일 가져오기</button>
	{/if}

	{#if message}<p class="text-xs text-semantic-red" role="alert">{message}</p>{/if}

	<section aria-label="가져오기 이력" class="flex flex-col gap-2">
		<h2 class="text-xs font-semibold text-fg-primary">최근 가져오기</h2>
		{#if history === null}
			<p class="text-xs text-fg-muted">이력을 불러오지 못했어요</p>
		{:else if history.length === 0}
			<p class="text-xs text-fg-muted">아직 가져온 적이 없어요</p>
		{:else}
			{#each history as h (h.id)}
				<p class="rounded-lg border border-border-subtle bg-surface-2 p-3 text-xs text-fg-secondary">
					{(h.finished_at ?? h.created_at ?? '').slice(0, 16).replace('T', ' ')}
					{#if h.state === 'done' && h.result} · 새 {h.result.new}건 · 보강 {h.result.enriched}건
					{:else if h.state === 'failed'} · <span class="text-semantic-red">실패</span>
					{:else} · 진행 중{/if}
				</p>
			{/each}
		{/if}
	</section>
</div>
