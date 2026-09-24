"""합성 데이터 UI 스모크 하네스 — 개인 데이터 없이 Flask+SvelteKit 화면을 브라우저로 검증한다.

실제 러닝 DB(pansongit 등)를 건드리지 않고, 시드된 임시 DB로 앱을 띄워 Playwright로 화면을
열어 본다. 에러 로그만으로는 못 잡는 "화면이 비어 있음/제목 없음/스크럽 안 됨" 류를 잡는 용도.
default 계정(`data/users/default`)은 쓰지 않는다 — DB 경로를 항상 명시적으로 넘긴다.

파일:
- seed_synth.py  — 합성 DB 생성(활동 14·웰니스 30일·메트릭·랩·스트림·마일스톤·플랜·Coach 스레드).
- serve_synth.py — 지정한 DB로 Flask 앱 기동(get_db_path 패치). 프론트는 `frontend/build`(v2)를 서빙.
- race_check.py  — 동시 GET 요청 부하(`database is locked`/500 회귀 확인).
- pw/            — Playwright 스크립트(node). smoke2(텍스트·가로 넘침) · sweep(요소 개수) ·
                   smoke(스크린샷+ACTIONS) · scrub(스트림 판독) · flow_checkin · flow_plan.

사용 (저장소 루트에서):
    python3 scripts/synth_smoke/seed_synth.py scripts/synth_smoke/out/running.db
    python3 scripts/synth_smoke/seed_synth.py scripts/synth_smoke/out/empty.db --empty
    (cd frontend && npm run build)                      # /v2 정적 빌드
    python3 scripts/synth_smoke/serve_synth.py scripts/synth_smoke/out/running.db 18099 &
    cd scripts/synth_smoke/pw && npm install            # 최초 1회 (브라우저는 ~/.cache/ms-playwright 재사용)
    BASE=http://127.0.0.1:18099 ROUTES=/v2/today,/v2/library node smoke2.mjs
스크린샷은 pw/shots/, DB는 out/ 아래(둘 다 git 무시).

스크린샷의 한글·이모지가 □로 나오면 서버에 폰트가 없는 것 — 화면 문제가 아니다. 사용자 폰트 폴더에 넣으면 된다:
    ~/.local/share/fonts/ 에 NotoSansKR.ttf, NotoEmoji.ttf (google/fonts 저장소 ofl/notosanskr, ofl/notoemoji) 저장 후 fc-cache -f
"""
