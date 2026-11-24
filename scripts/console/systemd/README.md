# 관제 콘솔 설치·공개 가이드

## 1. 로컬 서비스 (127.0.0.1:8765 만 바인딩)

    mkdir -p ~/.config/systemd/user && cp scripts/console/systemd/runpulse-console.service ~/.config/systemd/user/
    systemctl --user daemon-reload && systemctl --user enable --now runpulse-console.service
    curl -s http://127.0.0.1:8765/api/overview | head -c 200

중지: `systemctl --user disable --now runpulse-console.service`. 로그: `journalctl --user -u runpulse-console`.
앱 자체에는 인증이 없다 — 반드시 아래 Cloudflare Access 뒤에서만 외부에 노출한다.

## 2. Cloudflare Tunnel + Access (stationsage.dev)

비밀값(토큰·터널 자격증명)은 저장소에 두지 않는다. 아래는 사용자가 직접 수행한다.

1. `cloudflared tunnel login` → `cloudflared tunnel create runpulse-console`
2. `~/.cloudflared/config.yml`:

       tunnel: runpulse-console
       credentials-file: /home/ubuntu/.cloudflared/<터널ID>.json
       ingress:
         - hostname: console.stationsage.dev
           service: http://127.0.0.1:8765
         - service: http_status:404

3. `cloudflared tunnel route dns runpulse-console console.stationsage.dev`
4. `runpulse-tunnel.service` 를 `~/.config/systemd/user/` 에 복사 후 `systemctl --user enable --now runpulse-tunnel` (Access 앱을 먼저 만든 뒤 3번 DNS 라우트를 공개할 것).
5. Cloudflare Zero Trust → Access → Applications → Self-hosted: 도메인 `console.stationsage.dev`,
   정책 Allow = 본인 이메일 1개(원타임 PIN 또는 IdP). **Access 앱을 먼저 만든 뒤** DNS 라우트를 공개한다.
6. 확인: 시크릿 창에서 접속 시 Access 로그인 화면이 떠야 하고, 로그인 후 콘솔이 보여야 한다.

POST 는 Origin 이 Host 와 같아야 통과한다(CSRF 방어) — Cloudflare 가 Host 를 유지하므로 별도 설정 불필요.

## 3. Telegram 연동

루프 정지·사용자 결정 대기 발생 시 기존 notify 로 알림이 간다. 환경변수 `RUNPULSE_CONSOLE_URL=https://console.stationsage.dev`
를 루프를 실행하는 서비스(drop-in `Environment=`)에 주면 알림 말미에 콘솔 링크가 붙는다.
