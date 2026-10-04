// 03c-library.md 3-A — Library 홈. 히어로(archive)만 await, 나머지 블록은 LibraryBlock이 각자 로드한다.
import { getArchive } from '$lib/api/library';
import { invalidate } from '$app/navigation';
import { swrLoad } from '$lib/loadCache';
import type { ArchiveData } from '$lib/types';

export interface LibraryHomeData {
	archive: ArchiveData | null;
	archiveError: string | null;
}

// 탭 재방문 시 즉시 이전 값을 보여주고 조용히 갱신(02-performance.md P-5). 실패는 캐시되지 않는다.
export async function load({ depends }: { depends: (key: string) => void }): Promise<LibraryHomeData> {
	depends('app:library-home');
	try {
		const archive = await swrLoad('app:library-home', getArchive, invalidate);
		return { archive, archiveError: null };
	} catch (e) {
		return { archive: null, archiveError: (e as Error).message ?? '아카이브를 불러올 수 없습니다.' };
	}
}
