"""P7-PRED-32: 활동 기상 인제스트·캐시·폴백·충돌."""
from datetime import date

from src.metrics.base import CalcContext
from src.weather import provider as om
from src.weather.activity_weather import ingest_activity_weather
from tests.helpers_pred import mem_conn, seed_run
from tests.test_weather_provider import _hourly

om.MIN_INTERVAL_S = 0.0


class FakeGet:
    def __init__(self, resp):
        self.resp, self.calls = resp, []

    def __call__(self, url, params=None):
        self.calls.append((url, params))
        if isinstance(self.resp, Exception):
            raise self.resp
        return self.resp


def test_ingest_open_meteo_then_cache_hit():
    c = mem_conn()
    a1 = seed_run(c, sid="1", date="2026-07-01", t="07:00:00", moving=3600, temp=None)   # 중간 07:30
    seed_run(c, sid="2", date="2026-07-01", t="18:00:00", moving=1800)                  # 같은 좌표·날짜 → 캐시
    g = FakeGet(_hourly())
    st = ingest_activity_weather(c, g, today=date(2026, 9, 26))
    assert len(g.calls) == 1 and st["open_meteo"] == 2 and st["requests"] == 1
    ctx = CalcContext(conn=c, scope_type="activity", scope_id=str(a1))
    assert ctx.get_activity_metric(a1, "weather_temp_c") == 23.75
    assert ingest_activity_weather(c, g, today=date(2026, 9, 26))["open_meteo"] == 0     # 재실행 시 대상 없음


def test_offline_falls_back_to_device_and_retries_later():
    c = mem_conn()
    aid = seed_run(c, sid="1", date="2026-07-01", temp=24.0)
    st = ingest_activity_weather(c, FakeGet(OSError("offline")), today=date(2026, 9, 26))
    assert st["failed_requests"] == 1 and st["device_corrected"] == 1
    ctx = CalcContext(conn=c, scope_type="activity", scope_id=str(aid))
    assert ctx.get_activity_metric(aid, "weather_temp_c") == 20.0            # (24−11)/0.65
    st2 = ingest_activity_weather(c, FakeGet(_hourly()), today=date(2026, 9, 26))
    assert st2["open_meteo"] == 1 and ctx.get_activity_metric(aid, "weather_temp_c") != 20.0   # open_meteo 가 primary


def test_no_coords_no_device():
    c = mem_conn()
    seed_run(c, sid="1", lat=None, lon=None, temp=None)
    g = FakeGet(_hourly())
    assert ingest_activity_weather(c, g)["no_data"] == 1 and g.calls == []


def test_conflict_flag():
    c = mem_conn()
    seed_run(c, sid="1", date="2026-07-01", t="07:00:00", moving=3600, temp=40.0)   # 기기 보정 44.6 vs 23.75
    assert ingest_activity_weather(c, FakeGet(_hourly()), today=date(2026, 9, 26))["conflicts"] == 1
