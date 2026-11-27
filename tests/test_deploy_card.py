"""운영 반영 실패 결정 카드 — 종류별 검토안·추천안 생성."""
import pytest

from scripts.autopilot.deploy_card import _TABLE, build_deploy_card


@pytest.mark.parametrize("kind", list(_TABLE))
def test_card_has_review_and_recommendation(kind):
    c = build_deploy_card(3, kind, "사유", units=5, commits=7)
    assert (c["id"], c["kind"], c["status"]) == ("DEPLOY-R3", "deploy_failed", "open")
    assert c["review"] and c["recommend_why"] and c["diag"] == kind
    assert all(o["review"] and o["action"] for o in c["options"])
    assert c["recommendation"] in {o["key"] for o in c["options"]}


def test_recommendation_by_kind():
    def rec(k):
        c = build_deploy_card(1, k, "x")
        return next(o["action"] for o in c["options"] if o["key"] == c["recommendation"])
    assert (rec("tests"), rec("build"), rec("dirty"), rec("diverged")) == ("fix_unit", "fix_unit", "hold", "hold")
    assert "fix_unit" not in {o["action"] for o in build_deploy_card(1, "dirty", "x")["options"]}
