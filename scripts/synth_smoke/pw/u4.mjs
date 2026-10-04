// U4: A-8/A-9 활동 상세·메트릭 탭이 DrillPanel(URL 스택)을 쓰는지 확인
import { chromium } from 'playwright';
const BASE = process.env.BASE; const ID = process.env.ACT_ID;
const b = await chromium.launch(); const p = await b.newPage();
let fail = 0;
const ok = (n, c) => { console.log(c ? 'PASS' : 'FAIL', n); if (!c) fail++; };
await p.goto(`${BASE}/v2/library/${ID}?drill=m.trimp`); await p.waitForTimeout(2500);
ok('deeplink restores panel', (await p.locator('h2:visible').filter({ hasText: /TRIMP|trimp/i }).count()) > 0 || (await p.locator('[role=dialog], .lg\\:border-l').count()) > 0);
await p.goto(`${BASE}/v2/library/${ID}?drill=m.nonexistent_zz`); await p.waitForTimeout(2000);
ok('unsupported slug light card', (await p.locator('[data-testid=drill-light]:visible').count()) > 0);
await p.goto(`${BASE}/v2/library/${ID}/metrics`); await p.waitForTimeout(2500);
const row = p.locator('button.flex.w-full.items-center.gap-3').first();
await row.click(); await p.waitForTimeout(2000);
ok('metrics row opens url drill', p.url().includes('drill=m.'));
await p.keyboard.press('Escape'); await p.waitForTimeout(800);
ok('esc closes', !p.url().includes('drill='));
await p.goto(`${BASE}/v2/library/metrics/ctl`); await p.waitForTimeout(2500);
await b.close(); process.exit(fail ? 1 : 0);
