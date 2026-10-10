# Phase 7 UI Renewal — 기술 아키텍처

**문서 상태**: Draft v0.2 — REVIEW-03 반영, §11 인증·멀티테넌시 신설  
**작성일**: 2026-06-10 (v0.1) / 2026-09-22 (v0.2)  
**전제 문서**: `00-diagnostic-and-direction.md` (B2 결정), `02-information-architecture.md`, `04-component-catalog.md`  
**후속 문서**: `06-data-layer-extensions.md`, `07-migration-roadmap.md`

---

## 이 문서의 목적

SvelteKit(프론트엔드) ↔ Flask(백엔드 API)의 경계, 빌드·배포 전략, PWA 오프라인 전략,  
개발 워크플로를 정의한다. 구현 전 합의해야 할 아키텍처 결정 사항을 기록한다.

---

## 1. 전체 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────────┐
│  단일 프로세스 (gunicorn)                                           │
│                                                                     │
│  ┌─────────────────────────────────┐                               │
│  │  Flask Application              │                               │
│  │                                 │                               │
│  │  /api/v1/*  → API 라우터        │ ← JSON API (SvelteKit 소비)   │
│  │  /v2/*      → SvelteKit 앱      │ ← 정적 파일 서빙              │
│  │  /*         → 기존 Flask HTML   │ ← v1 (마이그레이션 기간)      │
│  │                                 │                               │
│  │  src/services/  (D5)            │ ← 비즈니스 로직 레이어        │
│  │  src/calculators/               │ ← 메트릭 계산                 │
│  │  SQLite (running.db)            │ ← 현재 단일 파일(§11 참조)     │
│  └─────────────────────────────────┘                               │
│                                                                     │
│  ┌─────────────────────────────────┐                               │
│  │  SvelteKit (빌드 산출물)        │                               │
│  │  frontend/build/                │                               │
│  │  ├── _app/                      │                               │
│  │  ├── index.html                 │                               │
│  │  └── service-worker.js          │                               │
│  └─────────────────────────────────┘                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 결정 근거 (B2 variant)

- **단일 프로세스**: VPS 1대 운용, 프로세스 간 통신 오버헤드 없음
- **SvelteKit → 정적 빌드** (`adapter-static`): SSR 서버 불필요, Flask가 그대로 서빙
- **Flask API JSON only**: 기존 데이터 파이프라인 유지, 뷰 레이어만 교체
- **SQLite 유지**: 단일 파일 DB의 운영 단순성. SaaS 확정(REVIEW-03 §8) 이후에도 기술 자체는
  유지하고, 격리는 파일 단위(`email@db`)로 확장하는 방향 — §11 참조. P8은 P8'(Data
  Ownership & Transparency)로 재해석됨(00 §6)

---

## 2. 디렉터리 구조

```
RunPulse/
├── frontend/                    ← SvelteKit 프로젝트 루트 (신규)
│   ├── src/
│   │   ├── lib/
│   │   │   ├── api/             ← Flask API 클라이언트 함수
│   │   │   │   ├── today.ts
│   │   │   │   ├── metrics.ts
│   │   │   │   ├── activities.ts
│   │   │   │   ├── plan.ts
│   │   │   │   └── coach.ts
│   │   │   ├── components/      ← C1~C7 컴포넌트
│   │   │   │   ├── EvidenceQuote.svelte
│   │   │   │   ├── MetricCell.svelte
│   │   │   │   ├── MetricBreakdown.svelte
│   │   │   │   ├── ProviderComparison.svelte
│   │   │   │   ├── QuickInput.svelte
│   │   │   │   ├── RecommendationCard.svelte
│   │   │   │   └── TimelineNarrative.svelte
│   │   │   ├── stores/          ← Svelte stores (전역 상태)
│   │   │   │   ├── today.ts
│   │   │   │   ├── panel.ts     ← 우측 패널 상태
│   │   │   │   └── prefs.ts     ← 사용자 환경설정 (Provider 우선순위 등)
│   │   │   └── types/           ← 공유 TypeScript 타입
│   │   │       └── index.ts
│   │   └── routes/              ← SvelteKit 라우트 (02-IA 매핑)
│   │       ├── today/       ← L0~L3, 구 story·plan(보기) 흡수
│   │       ├── library/
│   │       ├── coach/       ← 구 plan(작업) 흡수
│   │       └── data/        ← ☰ 메뉴 산하
│   ├── static/
│   │   ├── manifest.json        ← PWA 매니페스트
│   │   └── icons/
│   ├── build/                   ← 빌드 산출물 (gitignore)
│   ├── svelte.config.js
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   └── package.json
│
├── src/                         ← 기존 Python 백엔드 (유지)
│   ├── api/                     ← Flask API 라우터 (신규)
│   │   ├── __init__.py
│   │   ├── routes_today.py      ← /today/narrative, /today/milestones 포함(구 story 흡수)
│   │   ├── routes_library.py
│   │   ├── routes_plan.py       ← Today(보기)·Coach(작업) 양쪽이 소비
│   │   ├── routes_coach.py
│   │   └── routes_data.py
│   ├── services/                ← D5: 서비스 레이어 (Phase 7a 전제조건)
│   ├── calculators/
│   └── ...기존 코드
│
└── serve.py                     ← Flask 진입점 (정적 서빙 경로 추가)
```

---

## 3. Flask API 설계

### 3.1 URL 규칙

```
/api/v1/{영역}/{리소스}
```

버전 prefix `/api/v1/`는 SvelteKit 라우트(`/today`, `/library` 등)와 충돌하지 않는다.

### 3.2 엔드포인트 목록

#### Today

```
GET  /api/v1/today
     → { status: TodayStatus, briefing: Briefing, session: Session|null,
         recent_activities: Activity[] }

GET  /api/v1/today/status
     → { utrs, cirs, tsb, ...지표 }

POST /api/v1/today/checkin
     Body: { fatigue: int, pain: str, note: str }
     → { id: int, saved_at: str }

GET  /api/v1/today/narrative?year=2026&month=6
     → { summary: str, body: NarrativeSegment[], highlights: Highlights }
     ← 구 /api/v1/story 흡수. Today L2 "성장 내러티브" 전용(03a-today.md 1-C)

GET  /api/v1/today/milestones
     → { milestones: Milestone[] }
     ← 구 /api/v1/story/milestones 흡수
```

#### Library

```
GET  /api/v1/library/activities?sport=running&from=&to=&page=1&per_page=20
     → { activities: Activity[], total: int, has_more: bool }

GET  /api/v1/library/activities/:id
     → { activity: ActivityDetail }

GET  /api/v1/library/activities/:id/streams
     → { streams: { pace[], hr[], altitude[], cadence[], ... } }

GET  /api/v1/library/metrics?group=fitness&provider=
     → { groups: MetricGroup[] }

GET  /api/v1/library/metrics/:slug?period=3m&provider=
     → { metric: MetricDetail, trend: TrendPoint[], breakdown: BreakdownNode }

GET  /api/v1/library/wellness?from=&to=
     → { entries: WellnessEntry[] }

GET  /api/v1/library/providers?activity_id=&from=&to=
     → { comparison: ComparisonRow[] }
```

#### Plan

*도메인 리소스로 유지 — IA 탭이 API 경계를 결정하지 않는다(00 §4.1). Today L2가 "보기"로,
Coach(`03e-coach.md` 5-C~5-G)가 "작업"으로 동일 엔드포인트를 소비한다.*

```
GET  /api/v1/plan/active
     → { program: Program|null }

GET  /api/v1/plan/:id
     → { program: ProgramDetail }

POST /api/v1/plan/generate
     Body: { race_distance, race_date, goal_time, style }
     → { options: ProgramOption[] }   ← 3~5개 선택지

POST /api/v1/plan
     Body: { option_id: str }
     → { program: Program }

GET  /api/v1/plan/:id/session/:week/:day
     → { session: Session, adjustments: Adjustment[] }

PUT  /api/v1/plan/:id/session/:week/:day/accept-adjustment
     → { session: Session }
```

#### Coach

```
GET  /api/v1/coach/threads
     → { threads: Thread[] }

GET  /api/v1/coach/threads/:id
     → { thread: ThreadDetail, messages: Message[] }

POST /api/v1/coach/threads/:id/messages
     Body: { content: str }
     → { message: Message }   ← AI 응답 포함

POST /api/v1/coach/threads
     Body: { initial_message: str }
     → { thread: Thread, message: Message }
```

#### Data

```
GET  /api/v1/data/sources
     → { sources: SourceStatus[] }

POST /api/v1/data/sync
     Body: { sources: str[], days: int }
     → { job_id: str }

GET  /api/v1/data/sync/status/:job_id
     → { status: str, progress: int, log: str[] }

GET  /api/v1/data/settings
     → { settings: AppSettings }

PUT  /api/v1/data/settings
     Body: Partial<AppSettings>
     → { settings: AppSettings }
```

### 3.3 공통 응답 형식

```typescript
// 성공
{
  data: T,
  meta?: { total?: number, page?: number, ... }
}

// 에러
{
  error: {
    code: string,       // e.g. "NOT_FOUND", "SYNC_RUNNING"
    message: string
  }
}
```

### 3.4 Flask 라우터 구조 (Python)

```python
# src/api/__init__.py
from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

from .routes_today import *
from .routes_library import *
# ...

# serve.py (기존)
from src.api import api_bp
app.register_blueprint(api_bp)

# SvelteKit 정적 파일 서빙 추가
@app.route('/v2/', defaults={'path': ''})
@app.route('/v2/<path:path>')
def serve_v2(path):
    static_dir = Path('frontend/build')
    file_path = static_dir / path
    if file_path.is_file():
        return send_from_directory(static_dir, path)
    return send_from_directory(static_dir, 'index.html')  # SPA fallback
```

---

## 4. SvelteKit 설정

### 4.1 adapter-static 설정

```javascript
// svelte.config.js
import adapter from '@sveltejs/adapter-static';

export default {
  kit: {
    adapter: adapter({
      pages: 'build',
      assets: 'build',
      fallback: 'index.html',   // SPA 모드 (Flask가 라우팅 처리)
    }),
    paths: {
      base: '/v2'               // Flask 서빙 경로와 일치
    }
  }
};
```

### 4.2 API 클라이언트 기본 구조

```typescript
// frontend/src/lib/api/client.ts

const API_BASE = import.meta.env.DEV
  ? 'http://localhost:5000/api/v1'   // 개발: Flask 직접
  : '/api/v1';                       // 프로덕션: 동일 오리진

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) throw await res.json();
  return (await res.json()).data as T;
}

export { apiFetch };
```

### 4.3 SvelteKit 라우트 → API 매핑

```
/today                    → GET /api/v1/today (+ /today/narrative, /today/milestones)
/library/activities       → GET /api/v1/library/activities
/library/activities/[id]  → GET /api/v1/library/activities/[id]
/library/metrics          → GET /api/v1/library/metrics
/library/metrics/[slug]   → GET /api/v1/library/metrics/[slug]
/coach                    → GET /api/v1/coach/threads
/coach/[threadId]         → GET /api/v1/coach/threads/[threadId]
/coach/plan               → GET /api/v1/plan/active
/coach/plan/new           → POST /api/v1/plan/generate
/data                     → GET /api/v1/data/sources   (☰ 메뉴 산하)
```

### 4.4 전역 상태 관리 (Svelte stores)

```typescript
// frontend/src/lib/stores/panel.ts
// 우측 패널 / 슬라이드업 시트 전역 제어

import { writable } from 'svelte/store';

type PanelContent =
  | { type: 'metric_breakdown'; slug: string; provider: string }
  | { type: 'evidence'; evidenceProps: EvidenceQuoteProps }
  | null;

export const panelContent = writable<PanelContent>(null);

export function openPanel(content: PanelContent) {
  panelContent.set(content);
}

export function closePanel() {
  panelContent.set(null);
}
```

```typescript
// frontend/src/lib/stores/prefs.ts
// Provider 우선순위 등 사용자 설정 (localStorage 동기화)

import { writable } from 'svelte/store';
import { browser } from '$app/environment';

type Prefs = {
  providerPriority: Record<string, string>;  // slug → provider
  useV2: boolean;                             // 베타 토글
};

const defaultPrefs: Prefs = {
  providerPriority: {},
  useV2: false,
};

function createPrefsStore() {
  const initial = browser
    ? JSON.parse(localStorage.getItem('runpulse_prefs') ?? 'null') ?? defaultPrefs
    : defaultPrefs;

  const { subscribe, set, update } = writable<Prefs>(initial);

  return {
    subscribe,
    set: (v: Prefs) => {
      if (browser) localStorage.setItem('runpulse_prefs', JSON.stringify(v));
      set(v);
    },
    update,
  };
}

export const prefs = createPrefsStore();
```

---

## 5. 빌드 및 배포

### 5.1 개발 환경

```
터미널 1: Flask 개발 서버
  python serve.py              # 포트 5000

터미널 2: SvelteKit 개발 서버
  cd frontend && npm run dev   # 포트 5173 (Vite)
  → CORS: Flask에서 개발 중 5173 허용
  → API 요청: 5173 → 5000 (Vite proxy or 직접)
```

Vite 프록시 설정:
```typescript
// vite.config.ts
export default {
  server: {
    proxy: {
      '/api': 'http://localhost:5000',
    }
  }
};
```

### 5.2 프로덕션 빌드

```bash
# 1. SvelteKit 빌드
cd frontend && npm run build
# → frontend/build/ 생성

# 2. Flask 정적 파일 경로 확인
# serve.py가 frontend/build/ 서빙

# 3. gunicorn 실행 (기존과 동일)
gunicorn serve:app --bind 0.0.0.0:5000 --workers 1
```

### 5.3 Makefile 타깃 (제안)

```makefile
build-frontend:
    cd frontend && npm ci && npm run build

dev:
    # 두 서버 동시 실행 (tmux or concurrently)
    concurrently "python serve.py" "cd frontend && npm run dev"

deploy:
    make build-frontend
    sudo systemctl restart runpulse
```

### 5.4 정적 파일 캐시 전략

```python
# serve.py — 정적 파일 서빙 시 캐시 헤더

@app.route('/v2/<path:path>')
def serve_v2(path):
    static_dir = Path('frontend/build')
    file_path = static_dir / path
    if file_path.is_file():
        # 해시된 JS/CSS는 장기 캐시, index.html은 no-cache
        if path.startswith('_app/'):
            resp = send_from_directory(static_dir, path)
            resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            return resp
        return send_from_directory(static_dir, path)
    resp = send_from_directory(static_dir, 'index.html')
    resp.headers['Cache-Control'] = 'no-cache'
    return resp
```

---

## 6. PWA 전략 (P8' Data Ownership & Transparency)

서버 가공(SaaS, REVIEW-03 §8) 모델이므로 "오프라인 = 로컬 DB"가 아니라 "오프라인 =
Service Worker가 캐시한 최근 API 응답"이다 — 표현을 이에 맞춰 정정.

### 6.1 오프라인 지원 범위

| 영역 | 오프라인 동작 | 캐시 전략 |
|------|-------------|-----------|
| Today L0~L1 | 정상 (캐시된 최근 응답) | Cache-first (API) |
| Today L2 (내러티브) | 정상 (캐시된 내러티브) | Stale-while-revalidate |
| Library/activities | 정상 (캐시된 응답) | Cache-first |
| Library/metrics | 정상 (캐시된 응답) | Cache-first |
| Coach — 플랜 열람 (Today L2 연동분) | 정상 (캐시된 응답) | Cache-first |
| Coach (대화 열람) | 이전 대화 열람 가능 | Cache-first |
| Coach (새 메시지) | 오류 표시, 큐에 저장 | Network-first + 큐 |
| Data/sync | 불가 | Network-only |

### 6.2 Service Worker 캐시 전략

```javascript
// static/service-worker.js (Vite PWA 플러그인 사용 또는 수동)

const STATIC_CACHE = 'runpulse-static-v1';
const API_CACHE = 'runpulse-api-v1';

const CACHE_FIRST_APIS = [
  '/api/v1/today',              // /today/narrative, /today/milestones 포함(prefix 매칭)
  '/api/v1/library/activities',
  '/api/v1/library/metrics',
  '/api/v1/plan/active',
];

const NETWORK_FIRST_APIS = [
  '/api/v1/coach',
  '/api/v1/data/sync',
];

// 설치: 정적 파일 사전 캐시
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache =>
      cache.addAll(['/', '/v2/', '/v2/today', '/v2/library'])
    )
  );
});

// 요청 가로채기
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  if (CACHE_FIRST_APIS.some(p => url.pathname.startsWith(p))) {
    event.respondWith(cacheFirst(event.request, API_CACHE));
  } else if (NETWORK_FIRST_APIS.some(p => url.pathname.startsWith(p))) {
    event.respondWith(networkFirst(event.request, API_CACHE));
  }
  // 그 외: 브라우저 기본 동작
});
```

### 6.3 PWA 매니페스트

```json
// frontend/static/manifest.json
{
  "name": "RunPulse",
  "short_name": "RunPulse",
  "start_url": "/v2/today",
  "display": "standalone",
  "background_color": "#0f172a",
  "theme_color": "#0f172a",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

---

## 7. 베타 토글 구현

`/data/settings`의 "새 UI (v2) 사용" 토글이 활성화되면,  
기존 Flask HTML 화면의 내부 링크가 모두 `/v2/*` 경로로 전환된다.

### 7.1 Flask 측 (쿠키 기반)

```python
# src/views_settings.py
@app.route('/settings/toggle-v2', methods=['POST'])
def toggle_v2():
    use_v2 = request.json.get('use_v2', False)
    resp = jsonify({'ok': True})
    resp.set_cookie('use_v2', '1' if use_v2 else '0', max_age=365*24*3600)
    return resp

# 기존 HTML 뷰 — 베타 토글 ON이면 /v2/today로 리다이렉트
@app.route('/dashboard')
def dashboard():
    if request.cookies.get('use_v2') == '1':
        return redirect('/v2/today')
    return render_template('dashboard.html', ...)
```

### 7.2 SvelteKit 측 (prefs store 연동)

```typescript
// /data/settings 화면
import { prefs } from '$lib/stores/prefs';

async function handleV2Toggle(value: boolean) {
  await fetch('/settings/toggle-v2', {
    method: 'POST',
    body: JSON.stringify({ use_v2: value }),
    headers: { 'Content-Type': 'application/json' }
  });
  prefs.update(p => ({ ...p, useV2: value }));
}
```

---

## 8. 개발 의존성

### 8.1 SvelteKit 스택

```json
// frontend/package.json (주요 패키지)
{
  "dependencies": {
    "@sveltejs/kit": "^2.x",
    "svelte": "^5.x"
  },
  "devDependencies": {
    "@sveltejs/adapter-static": "^3.x",
    "tailwindcss": "^3.x",
    "vite": "^5.x",
    "typescript": "^5.x",
    "@tailwindcss/typography": "^0.5.x"
  }
}
```

shadcn-svelte 사용 여부:  
→ C1~C7 컴포넌트가 모두 커스텀 구현이므로 **사용 최소화**.  
→ Dialog(우측 패널/시트), Tooltip 정도만 shadcn-svelte 차용.  
→ 나머지는 Tailwind + Svelte 네이티브로 구현.

### 8.2 Python 추가 의존성 없음

기존 Flask, gunicorn 유지. API 라우터 추가만.

---

## 9. 아키텍처 결정 사항 (ADR)

| ID | 결정 | 이유 | 대안 |
|----|------|------|------|
| ADR-V2-01 | `adapter-static` 사용 | Flask 단일 프로세스 서빙, SSR 불필요 | adapter-node (별도 Node 서버 — 복잡도 증가) |
| ADR-V2-02 | `/v2/` base path | v1 병행 운용, 충돌 없는 전환 | 서브도메인 분리 — DNS 관리 복잡 |
| ADR-V2-03 | Svelte 5 (runes) | 최신 reactive 모델, 보일러플레이트 감소 | Svelte 4 — 안정적이나 구식 |
| ADR-V2-04 | shadcn-svelte 최소 사용 | C1~C7이 도메인 특화 컴포넌트, UI 라이브러리 의존 최소화 | shadcn 전면 사용 — 커스터마이즈 충돌 |
| ADR-V2-05 | Service Worker: Cache-First (API) | P8' Data Ownership, 오프라인 Today/Library 필수 | Network-First — 오프라인 불가 |
| ADR-V2-07 | 인증은 Flask가 소유, SvelteKit은 세션 쿠키만 전달 | 인증 로직 이중화 방지, P8' 전송 범위 투명성과 일치 | 프론트엔드 토큰 관리 — 로직 중복·노출면 증가 |
| ADR-V2-06 | API 버전 `/api/v1/` | 미래 v2 API 공존 가능 | 버전 없음 — 호환성 깨짐 위험 |

---

## 10. 구현 전제조건 체크리스트

Phase 7 구현 시작 전 충족되어야 할 조건:

- [ ] **D5 완료**: `src/services/` 서비스 레이어 구현 (`AUDIT-SERVICE-LAYER` 해결)
  - API 라우터가 raw SQL 없이 서비스 레이어만 호출
- [ ] **D3 완료**: `user_inputs` 테이블 생성 (QuickInput 저장용)
- [ ] **D1 완료**: `json_value` 분해 스키마 표준화 (MetricBreakdown 계산 트리용)
- [ ] `frontend/` 디렉터리 초기화 (`npm create svelte@latest`)
- [ ] Flask `serve.py`에 `/v2/` 정적 서빙 + `/api/v1/` 블루프린트 등록

---

## 11. 인증·멀티테넌시 (REVIEW-03 §8·§10)

### 11.1 현재 상태

- 정식 로그인 기능 없음. Cloudflare Access가 GitHub email을 로그인 대체로 검증한다 — Flask는
  `CF-Access-Authenticated-User-Email` 헤더를 신뢰 소스로 사용(운영 환경, Cloudflare가
  요청 앞단에서 인증을 강제).
- DB는 사용자별 파일로 분리되어 있다 — `src/db_setup.py`의 `get_db_path(uid)`가 사용자 식별자로
  DB 파일 경로를 해석한다(2026-10 확인; 이전 서술 "단일 running.db, email@db는 로드맵"은 낡은 내용이었음).
  신규 가입자는 빈 DB로 시작하므로 생애주기 빈 상태(S1/S2)가 실제로 노출된다
  (`DESIGN-P7-REVIEW03-LIFECYCLE.md`).

### 11.2 인증 로드맵

- 1단계(현재): Cloudflare Access 단독.
- 2단계(로드맵): Google/Apple OAuth 정식 회원가입 오픈. Flask 세션에 인증된 이메일을
  저장하고, 이후 모든 API 라우터가 세션의 이메일로 DB 파일을 선택하는 구조로 전환.
- 인증 계층은 Flask(API 서버)가 소유한다 — SvelteKit은 세션 쿠키만 전달하고 인증 로직을
  프론트엔드에 두지 않는다(ADR-V2-07).

### 11.3 멀티테넌시 — email@db 격리 (범위 경계)

- 로드맵상 DB 경로 해석 규칙(예: `data/{email}/running.db`)으로의 전환은 **이 문서(Phase 7
  UI 리뉴얼)의 범위 밖**이다 — "데이터 레이어(D1~D5) 변경 없음, 순수 UI/IA 재설계"라는
  REVIEW-03 §7 원칙과 같은 이유로, DB 파일 라우팅은 별도 시스템 아키텍처 설계·ADR이
  필요한 결정이다(마이그레이션 스크립트, 파일 권한, 백업 전략 등이 얽힘).
- 이 문서의 API/SvelteKit 설계는 이 경계에 영향받지 않는다 — `apiFetch()`는 항상 동일
  오리진 요청이고, 어느 DB 파일을 쓸지는 서버가 세션으로 결정하므로 프론트엔드 코드
  변경이 필요 없다. Phase 7a~7d 구현은 현재의 단일 파일 DB를 그대로 전제해도 무방하다.

### 11.4 export — P8' 요건 (미배정)

- P8'(00 §6)의 "언제든 export 가능" 요건을 만족할 `GET /api/v1/data/export` 엔드포인트가
  아직 API 목록(§3.2)에도, `07-migration-roadmap.md`의 어느 단계에도 배정되지 않았다.
  Phase 7d "Data 화면"(`03f-data.md`) 범위에 포함할지는 판단 보류 — 이번 세션 범위 밖.

---

## 작성 이력

- v0.2 (2026-09-22): REVIEW-03 반영 — §1/§6의 "로컬 퍼스트(P8)" 표현을 P8'로 정정.
  Story API(`/api/v1/story`)를 `/api/v1/today/narrative`·`/today/milestones`로 흡수.
  디렉터리 구조·라우트 매핑·PWA 오프라인 표를 하단 3탭(Today/Library/Coach) 기준으로
  갱신. §11 인증·멀티테넌시 섹션 신설(CF Access 현황, OAuth 로드맵, email@db — 실제 DB
  라우팅 구현은 범위 밖으로 명시). ADR-V2-07 추가. export 엔드포인트 미배정 발견(§11.4,
  판단 보류).
- v0.1 (2026-06-10): 초안 — 전체 아키텍처, API 엔드포인트 목록, SvelteKit 설정, 빌드·배포 전략, PWA, 베타 토글, ADR 6개
