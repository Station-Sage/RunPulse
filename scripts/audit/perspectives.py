"""감사 관점 정의 — 관점별 모델(AUDIT_MODELS)과 프롬프트. 읽기 전용 트리아지 에이전트용(P3).

평시 감사는 haiku/sonnet 만 쓴다. Opus 는 릴리스(버전업) 감사(RELEASE_MODELS)에만, budget.opus_allowed 한도 안에서 쓴다.
모든 프롬프트에 제품 본질 블록(vision.VISION)이 들어가 '앱의 본질에 비춰' 결함의 무게를 판단한다.
관점은 입력(스윕 결과)을 서로 다른 질문으로 걸러, 기계 감지 노이즈와 실제 결함을 구분한다.
"""
from __future__ import annotations

from scripts.audit.vision import VISION

AUDIT_MODELS = {
    "ui": "haiku",        # 시각·레이아웃 결함 후보 분류 — 저렴한 모델로 충분
    "ux": "sonnet",       # 흐름·빈/오류 상태 안내의 적절성 판단
    "data": "sonnet",     # 값·단위·누락 의심(undefined/NaN, 4xx/5xx) 원인 추정
    "value": "sonnet",    # 러너에게 의미 있는 화면인지(가치) 판단
    "persona": "haiku",   # 초보 러너 페르소나로 이해 가능성 점검
    "vision": "sonnet",   # 제품 본질·원칙(근거·출처·투명성) 위배 여부
}
RELEASE_MODELS = {n: "opus" for n in AUDIT_MODELS}   # 버전업 감사 — 전 관점 Opus

FOCUS = {
    "ui": "레이아웃 깨짐, 가로 오버플로, 터치 타겟(24px 미만이 실제로 문제인지 인라인 링크 등 노이즈인지), 빈 화면.",
    "ux": "빈/오류 상태에서 사용자가 다음에 할 일을 알 수 있는지, 오류 상태 표식(error-state) 누락이 실제 결함인지 감지기 한계인지, h1 등 구조.",
    "data": "http 4xx/5xx·pageerror·undefined/NaN 누출의 원인이 앱 결함인지 합성 데이터/빈 DB 의 정상 응답인지.",
    "value": "화면이 러너의 의사결정(훈련·회복·대회)에 도움이 되는지, 이슈가 가치 훼손으로 이어지는지.",
    "vision": "근거 수치 없는 결론, 출처(Garmin/Strava 등) 불명 값, 드릴다운 불가한 수치, 소셜·라이브 추적류 본질 이탈 등 제품 원칙 위배.",
    "persona": "러닝 입문자 한국어 사용자가 용어·수치·오류 안내를 이해할 수 있는지.",
}

_PROMPT = """{vision}

너는 러닝 앱 RunPulse 의 '{name}' 관점 감사자다. 도구 없이 아래 기계 감지 결과만 보고 판단한다.
관점 초점: {focus}

규칙:
- 각 이슈 묶음(kind)을 실제 결함(real) / 감지기 노이즈(noise) / 판단 불가(unsure) 로 분류한다.
- real 은 사용자에게 보이는 영향 한 줄과 수정 방향 한 줄을 쓴다. 추측으로 real 을 남발하지 않는다. critical=true 는 데이터 손실·보안·핵심 기능 불능·잘못된 건강/훈련 수치 노출만(드물게).
- 출력은 JSON 배열만(설명·코드펜스 금지): [{{"kind":"...","verdict":"real|noise|unsure","impact":"...","fix":"...","critical":false,"cells":["셀id",...]}}]

기계 감지 이슈 묶음:
{groups}
"""


def build_prompt(perspective: str, groups: dict[str, list[dict]], max_cells: int = 6) -> str:
    """groups: kind → [{"cell","note"}]. 묶음당 대표 셀만 싣는다(토큰 절약)."""
    lines = []
    for kind, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        sample = "; ".join("%s (%s)" % (i["cell"], " ".join(i["note"].split())[:80]) for i in items[:max_cells])
        lines.append(f"- {kind}: {len(items)}건 — 예: {sample}")
    return _PROMPT.format(name=perspective, focus=FOCUS[perspective], vision=VISION, groups="\n".join(lines) or "(없음)")
