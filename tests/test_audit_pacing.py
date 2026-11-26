

def test_latest_observation_fills_utilization_from_unified_windows():
    from scripts.autopilot import pacing
    rl = {"rateLimitType": "five_hour", "status": "allowed", "resetsAt": 2000,
          "unifiedWindows": {"five_hour": {"utilization": 0.89, "resetsAt": 2000}}}
    assert pacing.latest_observation([{"rate_limit": rl}], "five_hour", 1000)["utilization"] == 0.89
