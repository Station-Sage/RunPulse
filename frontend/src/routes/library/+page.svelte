<script lang="ts">
	// 03c-library.md 3-A — Library 홈. 히어로 → 찾기 → 기록(PB) → 캘린더/월별 → 최근 활동 → 출처 요약.
	// 히어로만 라우트 load가 기다리고, 나머지 블록은 각자 로드·실패 격리(LibraryBlock).
	import type { LibraryHomeData } from './+page';
	import { base } from '$app/paths';
	import { invalidate } from '$app/navigation';
	import { getActivities } from '$lib/api/library';
	import { getProviderStatus, getProviderCoverage } from '$lib/api/providers';
	import ActivityRow from '$lib/components/ActivityRow.svelte';
	import ArchiveHero from '$lib/components/ArchiveHero.svelte';
	import ArchiveTabCard from '$lib/components/ArchiveTabCard.svelte';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import LibraryBlock from '$lib/components/LibraryBlock.svelte';
	import LibraryFinder from '$lib/components/LibraryFinder.svelte';
	import PersonalBests from '$lib/components/PersonalBests.svelte';
	import SourceSummary from '$lib/components/SourceSummary.svelte';
	import { swrEvict } from '$lib/loadCache';

	let { data }: { data: LibraryHomeData } = $props();

	const empty = $derived(!!data.archive && (data.archive.totals?.runs ?? 0) === 0);
	const fetchSources = async () => {
		const [status, coverage] = await Promise.all([getProviderStatus(), getProviderCoverage()]);
		return { status: status.providers, coverage };
	};
</script>

<svelte:head><title>Library · RunPulse</title></svelte:head>

{#if data.archiveError || !data.archive}
	<div class="px-4 pt-4">
		<ErrorState
			message="러닝 아카이브를 불러오지 못했어요"
			detail={data.archiveError ?? ''}
			onRetry={() => {
				swrEvict('app:library-home');
				invalidate('app:library-home');
			}}
		/>
	</div>
{:else if empty}
	<div class="flex flex-col items-center gap-3 px-4 py-16 text-center">
		<p class="text-base text-fg-primary">아직 가져온 러닝이 없어요</p>
		<p class="text-sm text-fg-muted">소스를 연결하고 동기화하면 여기에 내 기록이 쌓여요.</p>
		<a href="{base}/settings" class="rounded-lg bg-surface-3 px-4 py-2 text-sm text-fg-primary">소스 연결하기</a>
	</div>
{:else}
	<div class="flex flex-col gap-5 pb-8">
		<ArchiveHero archive={data.archive} />
		<LibraryFinder />
		<section class="px-4"><PersonalBests pbs={data.archive.personal_bests} /></section>
		<ArchiveTabCard archive={data.archive} />

		<section class="px-4" aria-label="최근 활동">
			<div class="mb-2 flex items-center justify-between">
				<h2 class="text-xs font-medium uppercase tracking-wide text-fg-muted">최근 활동</h2>
				<a href="{base}/library/activities" class="text-xs text-fg-muted hover:text-fg-secondary">전체 보기 →</a>
			</div>
			<LibraryBlock load={() => getActivities({ per_page: 5 })} skeletonClass="h-40">
				{#snippet children(res)}
					<ul class="divide-y divide-border-subtle rounded-xl border border-border-subtle bg-surface-2">
						{#each res.activities as act (act.id)}
							<li><ActivityRow {act} from="home" showProvider /></li>
						{/each}
					</ul>
				{/snippet}
			</LibraryBlock>
		</section>

		<section class="px-4" aria-label="내 데이터 출처">
			<h2 class="mb-2 text-xs font-medium uppercase tracking-wide text-fg-muted">내 데이터 출처</h2>
			<LibraryBlock load={fetchSources} skeletonClass="h-12">
				{#snippet children(s)}<SourceSummary coverage={s.coverage} status={s.status} />{/snippet}
			</LibraryBlock>
		</section>
	</div>
{/if}
