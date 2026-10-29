// 첫 페인트 전 수동 테마 적용(FOUC 방지). theme.ts 의 applyTheme 과 같은 동작이며 값은 THEME_COLORS 와 일치해야 한다.
try {
	var t = localStorage.getItem('rp-theme');
	if (t === 'light' || t === 'dark') {
		document.documentElement.dataset.theme = t;
		var c = t === 'light' ? '#f7f5f2' : '#0f172a';
		var m = document.querySelectorAll('meta[name="theme-color"]');
		for (var i = 0; i < m.length; i++) m[i].setAttribute('content', c);
	}
} catch (e) {}
