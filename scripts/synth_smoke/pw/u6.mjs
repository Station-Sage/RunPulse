// U6 A-10: ?seg=·?map=hr URL 복원 확인
import { chromium } from 'playwright';
const BASE = process.env.BASE; const ID = process.env.ACT_ID;
const b = await chromium.launch(); const p = await b.newPage();
let fail = 0;
const ok = (n, c) => { console.log(c ? 'PASS' : 'FAIL', n); if (!c) fail++; };
await p.goto(`${BASE}/v2/library/${ID}?seg=3`); await p.waitForTimeout(2500);
ok('seg=3 stays after load', p.url().includes('seg=3'));
await p.reload(); await p.waitForTimeout(2500);
ok('seg=3 survives refresh', p.url().includes('seg=3'));
const hrBtn = p.getByRole('button', { name: /심박/ }).first();
if (await hrBtn.count()) {
  await hrBtn.click(); await p.waitForTimeout(500);
  ok('map=hr synced', p.url().includes('map=hr'));
  await p.reload(); await p.waitForTimeout(2500);
  ok('map=hr survives refresh', p.url().includes('map=hr'));
} else console.log('SKIP map toggle (no hr range)');
await p.goto(`${BASE}/v2/library/${ID}/laps`); await p.waitForTimeout(2500);
ok('lap rows render', (await p.locator('[data-testid=lap-row]').count()) > 0);
ok('lap interval groups', (await p.locator('[data-testid=lap-group]').count()) >= 2);
ok('lap interval head', (await p.locator('[data-testid=lap-interval-head]').count()) === 1);
await b.close(); process.exit(fail ? 1 : 0);
