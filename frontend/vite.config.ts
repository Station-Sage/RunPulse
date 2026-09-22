import tailwindcss from '@tailwindcss/vite';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// Flask가 frontend/build/를 /v2/ 아래로 정적 서빙한다 (05-tech-architecture.md §3.4).
// 개발 서버는 실제 Flask 엔트리포인트(src/serve.py) 포트로 /api 요청을 프록시해
// CORS 설정 없이 동일 출처처럼 동작시킨다.
export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) => filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			adapter: adapter({ pages: 'build', assets: 'build', fallback: 'index.html' }),
			paths: { base: '/v2' }
		})
	],
	server: {
		proxy: {
			'/api': 'http://localhost:18080'
		}
	}
});
