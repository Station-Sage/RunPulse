"""루프 정지 사유 enum — 자유 문자열 매칭 대신 cycle_state.json 의 stop_reason 으로 정지/자동 재개를 판단한다.

사유별 재개 정책(타이머 발화 시 `resume`):
  pacing·step_cap : 그대로 재개(상태 유지)    round_done : 새 라운드(감사)로 재개
  failed          : 재개 안 함(알림만, --reset 필요)    stop_flag : 사람이 요청한 정지 — 재개 안 함
사용자 결정 대기(needs_decision)는 정지 사유가 아니다 — 그 항목만 건너뛰고 진행하며 state["pending_decisions"] 로만 노출한다.
"""
from __future__ import annotations

PACING, ROUND_DONE, FAILED, STOP_FLAG, STEP_CAP = "pacing", "round_done", "failed", "stop_flag", "step_cap"
ALL = (PACING, ROUND_DONE, FAILED, STOP_FLAG, STEP_CAP)
AUTO_RESUME = (PACING, ROUND_DONE, STEP_CAP)


def stop(st: dict, reason: str) -> None:
    if reason not in ALL:
        raise ValueError(f"알 수 없는 정지 사유: {reason}")
    st["stop_reason"] = reason


def is_stopped(st: dict) -> bool:
    return st.get("stop_reason") is not None


def resume(st: dict) -> bool:
    """타이머 발화 시 호출 — 자동 재개 가능한 사유면 정지를 풀고 True. 아니면 상태 유지 후 False."""
    r = st.get("stop_reason")
    if r is None:
        return True
    if r not in AUTO_RESUME:
        return False
    st["stop_reason"] = None
    if st.get("phase") in ("stopped", "halted"):
        st["phase"] = "audit"
    return True
