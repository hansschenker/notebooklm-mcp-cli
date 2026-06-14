"""Tests for RPC drift detection and RPC-level retry in BaseClient."""

from unittest.mock import patch

import pytest

from notebooklm_tools.core.base import BaseClient
from notebooklm_tools.core.errors import RPCDriftError


def _client():
    with patch.object(BaseClient, "_refresh_auth_tokens"):
        return BaseClient(cookies={}, csrf_token="t")


def test_drift_when_other_ids_present_but_not_ours():
    client = _client()
    parsed = [[["wrb.fr", "ROTATED", "[1]", None, None, None, "generic"]]]
    with pytest.raises(RPCDriftError) as exc:
        client._extract_rpc_result(parsed, "EXPECTED")
    msg = str(exc.value)
    assert "EXPECTED" in msg
    assert "ROTATED" in msg
    assert "NOTEBOOKLM_RPC_OVERRIDES" in msg


def test_empty_response_returns_none_not_drift():
    client = _client()
    assert client._extract_rpc_result([], "EXPECTED") is None


def test_matched_chunk_with_null_result_returns_none():
    client = _client()
    parsed = [[["wrb.fr", "EXPECTED", None, None, None, None, "generic"]]]
    assert client._extract_rpc_result(parsed, "EXPECTED") is None


def test_matched_chunk_returns_parsed_json():
    client = _client()
    parsed = [[["wrb.fr", "EXPECTED", "[1,2,3]", None, None, None, "generic"]]]
    assert client._extract_rpc_result(parsed, "EXPECTED") == [1, 2, 3]
