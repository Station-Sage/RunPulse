"""httpx 기반 HTTP GET/POST 래퍼. 재시도 및 에러 처리."""

import time
from typing import Any

import httpx


class ApiError(Exception):
    """API 호출 실패 예외."""

    def __init__(self, message: str, status_code: int = 0, body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


def get(
    url: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    auth: tuple[str, str] | None = None,
    timeout: int = 30,
) -> dict | list:
    """GET 요청. 실패 시 1회 재시도.

    Args:
        url: 요청 URL.
        headers: HTTP 헤더.
        params: 쿼리 파라미터.
        auth: (username, password) Basic Auth 튜플.
        timeout: 타임아웃 (초).

    Returns:
        JSON 응답 (dict 또는 list).

    Raises:
        ApiError: 2회 실패 시.
    """
    return _request("GET", url, headers=headers, params=params, auth=auth, timeout=timeout)


def get_with_headers(
    url: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    auth: tuple[str, str] | None = None,
    timeout: int = 30,
) -> tuple[dict | list, dict[str, str]]:
    """GET 요청 — (JSON 응답, 응답 헤더) 튜플 반환.

    Strava rate limit 헤더 등 응답 헤더가 필요한 경우 사용한다.

    Returns:
        (json_body, response_headers) 튜플.

    Raises:
        ApiError: 2회 실패 시.
    """
    return _request_raw(
        "GET", url, headers=headers, params=params, auth=auth, timeout=timeout
    )


def post(
    url: str,
    headers: dict[str, str] | None = None,
    data: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    auth: tuple[str, str] | None = None,
    timeout: int = 30,
) -> dict | list:
    """POST 요청. 실패 시 1회 재시도.

    Args:
        url: 요청 URL.
        headers: HTTP 헤더.
        data: form 데이터.
        json_body: JSON 바디.
        auth: (username, password) Basic Auth 튜플.
        timeout: 타임아웃 (초).

    Returns:
        JSON 응답 (dict 또는 list).

    Raises:
        ApiError: 2회 실패 시.
    """
    return _request(
        "POST", url, headers=headers, data=data, json_body=json_body,
        auth=auth, timeout=timeout,
    )


def _request(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    auth: tuple[str, str] | None = None,
    timeout: int = 30,
    _retries: int = 1,
) -> dict | list:
    """HTTP 요청 실행 (내부). 재시도 로직 포함."""
    last_error: Exception | None = None

    for attempt in range(_retries + 1):
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    data=data,
                    json=json_body,
                    auth=auth,
                )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            body = e.response.text[:500]
            print(f"[API] {method} {url} -> {status} (시도 {attempt + 1})")
            last_error = ApiError(
                f"{method} {url} failed: {status}", status_code=status, body=body,
            )
            # 4xx (클라이언트 오류)는 재시도해도 결과 동일 — 즉시 중단
            if 400 <= status < 500:
                break

        except httpx.RequestError as e:
            print(f"[API] {method} {url} -> 연결 오류 (시도 {attempt + 1}): {e}")
            last_error = ApiError(f"{method} {url} 연결 실패: {e}")

        if attempt < _retries:
            time.sleep(2)

    raise last_error  # type: ignore[misc]


def _request_raw(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    auth: tuple[str, str] | None = None,
    timeout: int = 30,
    _retries: int = 1,
) -> tuple[dict | list, dict[str, str]]:
    """HTTP 요청 — (JSON 응답, 응답 헤더) 반환. 재시도 로직 포함."""
    last_error: Exception | None = None

    for attempt in range(_retries + 1):
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.request(
                    method, url,
                    headers=headers, params=params,
                    data=data, json=json_body, auth=auth,
                )
            response.raise_for_status()
            return response.json(), dict(response.headers)

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            body = e.response.text[:500]
            print(f"[API] {method} {url} -> {status} (시도 {attempt + 1})")
            last_error = ApiError(
                f"{method} {url} failed: {status}",
                status_code=status,
                body=body,
            )
            if 400 <= status < 500:
                break

        except httpx.RequestError as e:
            print(f"[API] {method} {url} -> 연결 오류 (시도 {attempt + 1}): {e}")
            last_error = ApiError(f"{method} {url} 연결 실패: {e}")

        if attempt < _retries:
            time.sleep(2)

    raise last_error  # type: ignore[misc]
