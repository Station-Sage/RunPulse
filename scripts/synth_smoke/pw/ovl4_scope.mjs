// OVL-4 ScopeSheet: 처음 포커스·트랩·Esc·포커스 복귀 (375px)
import { chromium } from '/home/ubuntu/projects/RunPulse/scripts/synth_smoke/pw/node_modules/playwright/index.mjs';
const B = 'http://127.0.0.1:18205/v2';
const b = await chromium.launch({ executablePath: '/home/ubuntu/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome' });
const page = await (await b.newContext({ viewport: { width: 375, height: 812 } })).newPage();
await page.goto(B + '/coach', { waitUntil: 'networkidle' });
await page.getByText('새 대화 시작').click();
await page.locator('textarea').fill('이번 주 훈련 어땠어?');
const opener = page.getByRole('button', { name: /전송 범위|범위/ }).first();
if (await opener.count()) await opener.focus(), await opener.click();
else await page.keyboard.press('Control+Enter');
await page.waitForTimeout(800);
const dlg = page.getByRole('dialog', { name: '전송 범위' });
console.log('dialog count:', await dlg.count());
if (await dlg.count()) {
	console.log('focus inside:', await page.evaluate(() => !!document.activeElement?.closest('[role=dialog]')));
	for (let i = 0; i < 12; i++) await page.keyboard.press('Tab');
	console.log('trap ok:', await page.evaluate(() => !!document.activeElement?.closest('[role=dialog]')));
	await page.keyboard.press('Escape');
	await page.waitForTimeout(300);
	console.log('closed:', (await dlg.count()) === 0, 'url:', page.url());
}
await b.close();
