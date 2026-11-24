// 설치 가능(PWA) 조건용 최소 서비스 워커 — 관제 데이터는 항상 네트워크에서 가져온다(캐시 없음).
self.addEventListener('fetch', () => {});
