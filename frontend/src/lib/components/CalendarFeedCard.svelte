<script lang="ts">
	import {
		getCalendarFeed, issueCalendarFeed, revokeCalendarFeed, type CalendarFeed
	} from '$lib/api/calendarFeed';
	import { googleSubscribeUrl, lastAccessText } from '$lib/calendarFeed';

	let { initial }: { initial: CalendarFeed | null } = $props();
	let feed = $state<CalendarFeed | null>(initial);
	let busy = $state(false);
	let message = $state('');
	let confirm = $state<'rotate' | 'revoke' | null>(null);

	async function run(fn: () => Promise<CalendarFeed | void>, done: string) {
		busy = true;
		message = '';
		try {
			const r = await fn();
			feed = r ?? (await getCalendarFeed());
			message = done;
		} catch (e) {
			message = e instanceof Error ? e.message : '요청을 처리하지 못했어요';
		} finally {
			busy = false;
			confirm = null;
		}
	}

	const issue = () => run(() => issueCalendarFeed(false), '구독 주소를 만들었어요');
	const rotate = () => run(() => issueCalendarFeed(true), '새 주소로 바꿨어요. 이전 주소는 더 이상 동작하지 않아요');
	const revoke = () => run(() => revokeCalendarFeed(), '구독을 해제했어요');

	async function copy() {
		if (!feed?.url) return;
		try {
			await navigator.clipboard.writeText(feed.url);
			message = '주소를 복사했어요';
		} catch {
			message = '복사하지 못했어요. 주소를 길게 눌러 직접 복사해 주세요';
		}
	}
</script>

<section aria-label="캘린더 구독" class="flex flex-col gap-2 rounded-lg border border-border-subtle bg-surface-2 p-3">
	<h2 class="text-sm text-fg-primary">훈련 계획 캘린더 구독</h2>
	{#if feed === null}
		<p class="text-xs text-fg-muted">구독 상태를 불러오지 못했어요</p>
	{:else if !feed.enabled}
		<p class="text-xs text-fg-secondary">
			구글·애플 캘린더에 구독하면 계획이 바뀔 때 자동으로 반영돼요. 주소를 아는 사람은 누구나 볼 수 있으니 공유하지 마세요.
		</p>
		<button type="button" disabled={busy} onclick={issue}
			class="self-start rounded border border-border-subtle bg-surface-3 px-3 py-1.5 text-xs text-fg-primary disabled:opacity-60">
			구독 주소 만들기
		</button>
	{:else}
		{#if feed.revealable && feed.url}
			<input readonly value={feed.url} aria-label="구독 주소" onfocus={(e) => e.currentTarget.select()}
				class="rounded border border-border-subtle bg-surface-1 px-2 py-1 text-xs text-fg-secondary" />
			<div class="flex flex-wrap gap-2 text-xs">
				<button type="button" onclick={copy} class="rounded border border-border-subtle bg-surface-3 px-3 py-1.5 text-fg-primary">주소 복사</button>
				<a href={feed.webcal_url} class="rounded border border-border-subtle bg-surface-3 px-3 py-1.5 text-fg-primary">애플 캘린더로 열기</a>
				{#if feed.webcal_url}
					<a href={googleSubscribeUrl(feed.webcal_url)} target="_blank" rel="noopener noreferrer"
						class="rounded border border-border-subtle bg-surface-3 px-3 py-1.5 text-fg-primary">구글 캘린더에 추가</a>
				{/if}
			</div>
			<p class="text-xs text-fg-muted">구글 캘린더는 반영까지 몇 시간 걸릴 수 있어요(보통 {feed.refresh_hint_hours}~24시간).</p>
		{:else}
			<p class="text-xs text-fg-secondary">보안상 주소를 다시 보여줄 수 없어요. 재발급해야 다시 볼 수 있어요.</p>
		{/if}
		<p class="text-xs text-fg-muted">{lastAccessText(feed)}</p>
		<details class="text-xs text-fg-secondary">
			<summary class="cursor-pointer">담기는 정보</summary>
			<p class="mt-1">담김: {feed.contents.join(' · ')}</p>
			<p>담기지 않음: {feed.excluded.join(' · ')}</p>
		</details>
		{#if confirm}
			<div role="alertdialog" aria-label="확인" class="flex flex-col gap-2 rounded border border-border-subtle bg-surface-1 p-2 text-xs">
				<p class="text-fg-primary">
					{confirm === 'rotate'
						? '새 주소를 만들면 지금 구독 중인 캘린더는 업데이트가 멈춰요. 새 주소로 다시 구독해야 해요.'
						: '구독을 해제하면 주소가 즉시 무효가 되고 캘린더 앱의 일정은 더 이상 갱신되지 않아요.'}
				</p>
				<div class="flex gap-2">
					<button type="button" disabled={busy} onclick={confirm === 'rotate' ? rotate : revoke}
						class="rounded border border-border-subtle bg-surface-3 px-3 py-1.5 text-semantic-red disabled:opacity-60">
						{confirm === 'rotate' ? '재발급' : '해제'}
					</button>
					<button type="button" onclick={() => (confirm = null)} class="rounded border border-border-subtle px-3 py-1.5 text-fg-secondary">취소</button>
				</div>
			</div>
		{:else}
			<div class="flex gap-3 text-xs text-fg-secondary">
				<button type="button" class="underline" onclick={() => (confirm = 'rotate')}>주소 재발급</button>
				<button type="button" class="underline" onclick={() => (confirm = 'revoke')}>구독 해제</button>
			</div>
		{/if}
	{/if}
	{#if message}<p class="text-xs text-fg-secondary" role="status">{message}</p>{/if}
</section>
