<script lang="ts">
	import {
		downloadQuick, exportDownloadUrl, getExports, startArchive, type ExportItem, type ExportKind
	} from '$lib/api/data';
	import { expiryText, formatBytes, rangeBody } from '$lib/exports';
	import type { ExportPageData } from './+page';

	let { data }: { data: ExportPageData } = $props();
	let history = $state<ExportItem[] | null>(data.history);
	let from = $state('');
	let to = $state('');
	let busy = $state<ExportKind | null>(null);
	let message = $state('');

	const quick = [
		{ kind: 'quick_activities', title: '활동 CSV', desc: '같은 활동은 한 줄로 합치고 소스별 원값 열을 함께 담아요.' },
		{ kind: 'quick_wellness', title: '웰니스 CSV', desc: '수면·HRV·안정시 심박·바디배터리 등 일별 기록이에요.' },
		{ kind: 'quick_load', title: '부하 CSV', desc: '일별 CTL·ATL·TSB·ACWR이에요.' }
	] as const;
	const active = $derived(history?.some((h) => h.state === 'queued' || h.state === 'running') ?? false);

	async function refresh() {
		try {
			history = await getExports();
		} catch {
			/* 다음 폴링에서 다시 시도 */
		}
	}

	$effect(() => {
		if (!active) return;
		const t = setInterval(refresh, 2000);
		return () => clearInterval(t);
	});

	async function quickDownload(kind: (typeof quick)[number]['kind']) {
		busy = kind;
		message = '';
		try {
			await downloadQuick(kind, rangeBody(from, to));
		} catch (e) {
			message = e instanceof Error ? e.message : '내보내기에 실패했어요';
		} finally {
			busy = null;
		}
	}

	async function makeArchive() {
		busy = 'archive';
		message = '';
		try {
			await startArchive(rangeBody(from, to));
			message = '아카이브를 만들고 있어요. 끝나면 아래 목록에서 받을 수 있어요.';
		} catch (e) {
			message = e instanceof Error ? e.message : '아카이브를 시작하지 못했어요';
		} finally {
			busy = null;
			await refresh();
		}
	}
</script>

<svelte:head><title>내보내기 · RunPulse</title></svelte:head>

<div class="flex flex-col gap-3 px-4 py-4">
	<fieldset class="flex items-center gap-2 text-xs text-fg-secondary">
		<legend class="mb-1">기간 (비우면 전체)</legend>
		<input type="date" bind:value={from} aria-label="시작일" class="rounded border border-border-subtle bg-surface-2 px-2 py-1" />
		<span>~</span>
		<input type="date" bind:value={to} aria-label="종료일" class="rounded border border-border-subtle bg-surface-2 px-2 py-1" />
	</fieldset>

	{#each quick as q (q.kind)}
		<button
			type="button"
			disabled={busy !== null}
			onclick={() => quickDownload(q.kind)}
			class="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-2 p-3 text-left hover:bg-surface-3 disabled:opacity-60"
		>
			<span class="text-sm text-fg-primary">{q.title}{busy === q.kind ? ' · 만드는 중…' : ''}</span>
			<span class="text-xs text-fg-secondary">{q.desc}</span>
		</button>
	{/each}

	<button
		type="button"
		disabled={busy !== null || active}
		onclick={makeArchive}
		class="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-2 p-3 text-left hover:bg-surface-3 disabled:opacity-60"
	>
		<span class="text-sm text-fg-primary">전체 아카이브 (zip){active ? ' · 만드는 중…' : ''}</span>
		<span class="text-xs text-fg-secondary">테이블 CSV, 위 CSV 3종, 소스 원본 데이터, manifest를 한 파일로 묶어요. 7일간 받을 수 있어요.</span>
	</button>

	{#if message}<p class="text-xs text-fg-secondary" role="status">{message}</p>{/if}

	<section aria-label="아카이브 이력" class="flex flex-col gap-2">
		<h2 class="text-xs font-semibold text-fg-primary">아카이브 이력</h2>
		{#if history === null}
			<p class="text-xs text-fg-muted">이력을 불러오지 못했어요</p>
		{:else if history.length === 0}
			<p class="text-xs text-fg-muted">아직 만든 아카이브가 없어요</p>
		{:else}
			{#each history as h (h.id)}
				<div class="flex items-center justify-between rounded-lg border border-border-subtle bg-surface-2 p-3 text-xs">
					<span class="text-fg-secondary">
						{(h.finished_at ?? h.created_at ?? '').slice(0, 16).replace('T', ' ')}
						{#if h.state === 'done' && h.result} · {formatBytes(h.result.size_bytes)} · {expiryText(h)}
						{:else if h.state === 'expired'} · {expiryText(h)}
						{:else if h.state === 'failed'} · <span class="text-semantic-red">실패{h.error ? ` — ${h.error}` : ''}</span>
						{:else} · 만드는 중…{/if}
					</span>
					{#if h.state === 'done'}
						<a href={exportDownloadUrl(h.id)} data-sveltekit-reload class="text-fg-primary underline">받기</a>
					{/if}
				</div>
			{/each}
		{/if}
	</section>

	<a
		href="/training/export.ics"
		data-sveltekit-reload
		class="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-2 p-3 hover:bg-surface-3"
	>
		<span class="text-sm text-fg-primary">훈련 계획 캘린더 (.ics)</span>
		<span class="text-xs text-fg-secondary">현재 계획을 캘린더 앱으로 가져갈 수 있어요.</span>
	</a>

	<p class="text-xs text-fg-muted">
		이 파일들은 내 기기로만 내려받아요. 외부 AI로 보내는 데이터는
		<a href="/data/settings/ai" class="underline">AI 설정</a>에서 확인할 수 있어요.
	</p>
</div>
