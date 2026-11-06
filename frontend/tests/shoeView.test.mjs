import test from 'node:test';
import assert from 'node:assert/strict';
import { ApiError } from '../src/lib/api/client.ts';
import {
	emptyForm,
	formToInput,
	kindLabel,
	methodLabel,
	shoeChipText,
	shoeWriteError,
	sortShoes,
	statusMeta,
	validateShoeForm,
	wearPercent
} from '../src/lib/shoeView.ts';

test('sortShoes: replace → soon → ok → retired, 같은 상태는 최근 사용 순', () => {
	const shoes = [
		{ id: 1, status: 'ok', last_used: '2026-05-09' },
		{ id: 2, status: 'soon', last_used: '2026-05-01' },
		{ id: 3, status: 'retired', last_used: '2026-05-10' },
		{ id: 4, status: 'soon', last_used: '2026-05-05' },
		{ id: 5, status: 'replace', last_used: null }
	];
	assert.deepEqual(sortShoes(shoes).map((s) => s.id), [5, 4, 2, 1, 3]);
});

test('statusMeta: 상태별 라벨·색 (색만으로 전달하지 않도록 라벨 동반)', () => {
	assert.equal(statusMeta('ok').label, '충분');
	assert.equal(statusMeta('soon').bar, 'bg-semantic-amber');
	assert.equal(statusMeta('replace').text, 'text-semantic-red');
	assert.equal(statusMeta(null).label, '충분');
});

test('methodLabel: 직접/소스 이름/기본 규칙/미지정', () => {
	assert.equal(methodLabel('manual'), '직접');
	assert.equal(methodLabel('source', 'garmin'), 'Garmin');
	assert.equal(methodLabel('source', 'strava_export'), 'Strava 파일');
	assert.equal(methodLabel('rule'), '기본 규칙');
	assert.equal(methodLabel('none'), '미지정');
	assert.equal(kindLabel('treadmill'), '트레드밀');
	assert.equal(kindLabel(null), null);
});

test('wearPercent', () => {
	assert.equal(wearPercent(612, 700), 87);
	assert.equal(wearPercent(10, 0), 0);
});

test('validateShoeForm: 필수·범위 문구', () => {
	const v = { ...emptyForm(), name: ' ' };
	assert.equal(validateShoeForm(v).name, '이름을 입력해 주세요');
	assert.equal(validateShoeForm({ ...v, name: 'a'.repeat(61) }).name, '이름은 60자 이하로 입력해 주세요');
	const e = validateShoeForm({ ...v, name: 'Peg', initial_km: '3001', retire_km: '50.5' });
	assert.equal(e.initial_km, '0~3000 km 사이로 입력해 주세요');
	assert.equal(e.retire_km, '100~2000 km 사이 정수로 입력해 주세요');
	assert.deepEqual(validateShoeForm({ ...v, name: 'Peg', retire_km: '600' }), {});
});

test('formToInput: 빈 값은 null, 숫자 변환', () => {
	const input = formToInput({ ...emptyForm(), name: ' Peg ', initial_km: '300', default_for: 'road' });
	assert.deepEqual(input, {
		name: 'Peg', brand: null, model: null, category: 'daily', start_date: null,
		initial_distance_km: 300, retire_km: null, default_for: 'road', notes: null
	});
	const back = emptyForm({ name: 'A', initial_km: 0, retire_km_custom: 500, default_for: null });
	assert.equal(back.retire_km, '500');
	assert.equal(back.initial_km, '');
});

test('shoeWriteError: 409·400 은 서버 문구, 그 외 공통 문구', () => {
	const conflict = new ApiError(409, { error: { code: 'GEAR_LINKED', message: '이미 다른 신발에 연결돼 있어요' } });
	assert.equal(shoeWriteError(conflict), '이미 다른 신발에 연결돼 있어요');
	assert.match(shoeWriteError(new ApiError(500, {})), /서버 오류/);
	assert.match(shoeWriteError(new ApiError(0, { error: { code: 'NETWORK' } })), /연결이 끊겨/);
});

test('shoeChipText: 칩 method 라벨·신발 없음·미지정·비러닝', () => {
	const base = { status: 'ok', conflict: false, conflict_sources: [], source: null };
	assert.equal(shoeChipText({ ...base, id: 1, name: '페가수스 40', method: 'rule' }), '페가수스 40 (기본 규칙)');
	assert.equal(shoeChipText({ ...base, id: 1, name: 'P', method: 'source', source: 'garmin' }), 'P (Garmin)');
	assert.equal(shoeChipText({ ...base, id: null, name: null, method: 'manual' }), '신발 없음 (직접)');
	assert.equal(shoeChipText({ ...base, id: null, name: null, method: 'none' }), '신발 미지정');
	assert.equal(shoeChipText(null), '');
});
