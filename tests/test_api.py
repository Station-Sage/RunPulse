"""api.py httpx 래퍼 테스트."""

from unittest.mock import patch, MagicMock

import httpx
import pytest

from src.utils.api import get, post, ApiError


class TestGet:
    @patch("src.utils.api.httpx.Client")
    def test_success(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": "ok"}
        mock_resp.raise_for_status.return_value = None
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock(
            request=MagicMock(return_value=mock_resp)
        ))
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = get("https://api.example.com/test")
        assert result == {"data": "ok"}

    @patch("src.utils.api.httpx.Client")
    def test_retry_then_success(self, mock_client_cls):
        """첫 번째 실패, 두 번째 성공."""
        mock_resp_fail = MagicMock()
        mock_resp_fail.status_code = 500
        mock_resp_fail.text = "Server Error"
        mock_resp_fail.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=mock_resp_fail,
        )

        mock_resp_ok = MagicMock()
        mock_resp_ok.json.return_value = {"ok": True}
        mock_resp_ok.raise_for_status.return_value = None

        mock_inner = MagicMock()
        mock_inner.request.side_effect = [mock_resp_fail, mock_resp_ok]
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_inner)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        with patch("src.utils.api.time.sleep"):
            result = get("https://api.example.com/test")
        assert result == {"ok": True}

    @patch("src.utils.api.httpx.Client")
    def test_double_failure_raises(self, mock_client_cls):
        """2회 모두 실패 시 ApiError."""
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.text = "Unavailable"
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "503", request=MagicMock(), response=mock_resp,
        )

        mock_inner = MagicMock()
        mock_inner.request.return_value = mock_resp
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_inner)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        with patch("src.utils.api.time.sleep"):
            with pytest.raises(ApiError) as exc_info:
                get("https://api.example.com/test")
            assert exc_info.value.status_code == 503


class TestPost:
    @patch("src.utils.api.httpx.Client")
    def test_post_json(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"token": "new"}
        mock_resp.raise_for_status.return_value = None
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock(
            request=MagicMock(return_value=mock_resp)
        ))
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = post("https://api.example.com/token", json_body={"grant": "refresh"})
        assert result == {"token": "new"}
