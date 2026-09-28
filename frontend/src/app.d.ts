// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		interface PageState {
			// §C3.1/C3.3 드릴다운 스택 — pushState 직후엔 이 값이, 새로고침·딥링크 직후엔
			// page.url의 `drill` 쿼리로 초기화된다(pushState는 page.url을 갱신하지 않는다).
			drill?: string[];
		}
		// interface Platform {}
	}
}

export {};
