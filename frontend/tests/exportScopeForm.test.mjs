import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const form = readFileSync(new URL('../src/lib/components/ExportScopeForm.svelte', import.meta.url), 'utf8');
const dlg = readFileSync(new URL('../src/lib/components/ExportConfirmDialog.svelte', import.meta.url), 'utf8');
const page = readFileSync(new URL('../src/routes/data/export/+page.svelte', import.meta.url), 'utf8');

test('범위 폼: fieldset/legend·체크박스 44px·민감 표시·해제 기록 하위 선택', () => {
	assert.match(form, /<fieldset/);
	assert.match(form, /<legend/);
	assert.match(form, /tap/);
	assert.match(form, /민감 정보 포함/);
	assert.match(form, /해제한 기록도 포함/);
	assert.match(form, /disabled=\{!selected\.includes\('episodes'\)\}/);
});

test('확인 대화상자: modal·취소 경로', () => {
	assert.match(dlg, /use:modal/);
	assert.match(dlg, /onclick=\{onCancel\}/);
});

test('페이지: 취소하면 요청 없이 닫고, 확인에서만 makeArchive', () => {
	assert.match(page, /onConfirm=\{makeArchive\}/);
	assert.match(page, /onCancel=\{\(\) => \(confirmOpen = false\)\}/);
	assert.match(page, /aria-live="polite"/);
	assert.match(page, /다시 만들기/);
});
