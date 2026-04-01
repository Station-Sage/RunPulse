# src/metrics/ GUIDE — 2차 메트릭 계산 엔진

## 구조
- **engine.py**: 배치 오케스트레이터. 모든 메트릭의 일괄 계산/재계산 담당.
- **store.py**: `computed_metrics` 테이블 UPSERT/조회 헬퍼.
- **개별 메트릭 파일**: 하나의 메트릭 = 하나의 파일. `calc_*()` 함수 export.

## 파일 맵

### 엔진/저장
| 파일 | 역할 |
|------|------|
| `engine.py` | `run_for_date()`, `run_for_date_range()`, `recompute_all()` |
| `store.py` | `save_metric()`, `load_metric()`, `load_metric_series()` |

### 일별 메트릭 — `calc_*(conn, date: str) -> float | None`
| 파일 | 메트릭 | 설명 |
|------|--------|------|
| `acwr.py` | ACWR | 급성/만성 부하 비율 |
| `adti.py` | ADTI | 유산소 분리 추세 |
| `cirs.py` | CIRS | 복합 부상 위험 |
| `ctl_atl.py` | CTL/ATL | 자체 계산 피트니스/피로 |
| `lsi.py` | LSI | 부하 스파이크 지수 |
| `monotony.py` | Monotony/Strain | 단조로움 + 스트레인 |
| `sapi.py` | SAPI | 계절 성과 비교 |
| `teroi.py` | TEROI | 훈련 ROI |
| `tids.py` | TIDS | 훈련 강도 분포 |
| `trimp.py` | TRIMP/HRSS | TRIMPexp + HR 기반 부하 |
| `utrs.py` | UTRS | 통합 훈련 준비도 |

### 활동별 메트릭 — `calc_*(conn, activity_id: int) -> float | dict | None`
| 파일 | 메트릭 | 설명 |
|------|--------|------|
| `decoupling.py` | Decoupling/EF | 유산소 분리 + 효율 팩터 |
| `di.py` | DI | 내구성 지수 (90분+ 세션 필요) |
| `fearp.py` | FEARP | 환경 보정 페이스 (날씨+경사) |
| `gap.py` | GAP/NGP | 경사 보정 페이스 |
| `rec.py` | REC | 러닝 효율성 |
| `relative_effort.py` | RE | Relative Effort (Strava 방식) |
| `rmr.py` | RMR | 러너 성숙도 레이더 5축 |
| `rri.py` | RRI | 레이스 준비도 지수 |
| `rtti.py` | RTTI | 러닝 내성 훈련 지수 |
| `tpdi.py` | TPDI | 실내/야외 퍼포먼스 격차 |
| `wlei.py` | WLEI | 날씨 가중 노력 지수 |

### 복합/참조
| 파일 | 역할 |
|------|------|
| `crs.py` | CRS Gate 5종 (훈련 엔진 연동) |
| `critical_power.py` | Critical Power / W' |
| `daniels_table.py` | Daniels VDOT 참조 테이블 |
| `darp.py` | DARP 레이스 예측 (VDOT+DI) |
| `eftp.py` | eFTP (추정 기능적 역치 페이스) |
| `marathon_shape.py` | Marathon Shape (Runalyze 방식) |
| `vdot.py` | VDOT 계산 |
| `vdot_adj.py` | VDOT HR-페이스 보정 |
| `workout_classifier.py` | 운동 유형 자동 분류 |

## 규칙
1. **데이터 없으면 `None` 반환** — UI에서 "데이터 수집 중" 표시. 절대 에러 발생 금지.
2. 계산식은 `v0.2/.ai/metrics.md` (PDF 원본) 기준. 차이 시 PDF 우선.
3. 모든 저장은 `store.save_metric()` 사용. 직접 SQL 금지.
4. DI: 90분+ 세션 8주 3회 미달 → `None`.
5. FEARP: GPS 고도 없으면 `grade_factor=1.0`, 날씨 API 실패 시 `temp=15, humidity=50`.
6. CIRS 가중치: `ACWR×0.4 + Monotony×0.2 + Spike×0.3 + Asym×0.1`.
7. 숫자 계산은 반드시 Python에서 수행. LLM은 해석/서술/계획 생성에만 활용

## 새 메트릭 추가 체크리스트
1. `src/metrics/<name>.py` 생성 — `calc_<name>()` 함수 export
2. `engine.py`에 호출 추가 (일별 or 활동별)
3. `store.save_metric()` 으로 저장
4. 테스트 `tests/test_<name>.py` 작성
5. 이 GUIDE.md 파일맵에 추가

## 의존성
- `src/weather/provider.py` — FEARP, WLEI 날씨 데이터
- `src/web/` — 뷰에서 `store.load_metric()` 으로 조회
- `src/training/crs.py`가 아닌 `src/metrics/crs.py` — 훈련 엔진이 참조
