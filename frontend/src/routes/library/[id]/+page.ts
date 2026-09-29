export type { ActivityLayoutData as ActivityPageData } from './+layout';

// 로드 없음 — +layout.ts가 1회 가져온 활동 상세를 그대로 상속한다(02-performance.md P-4,
// 서브탭 전환마다 650KB를 재요청하던 걸 제거).
