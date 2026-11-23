# 감사 사이클 스케줄 (미설치 상태로 제공)

    mkdir -p ~/.config/systemd/user && cp scripts/audit/systemd/runpulse-audit.* ~/.config/systemd/user/
    systemctl --user daemon-reload && systemctl --user enable --now runpulse-audit.timer

타이머는 약 100분마다 `loop`(단계 1개 수행) 를 부를 뿐이며, 세션 80%·주간 목표 사용률(pacing)과 90분 최소 간격이 대부분의 호출을 건너뛰게 한다(무한 반복 아님).
중지: `systemctl --user disable --now runpulse-audit.timer`
