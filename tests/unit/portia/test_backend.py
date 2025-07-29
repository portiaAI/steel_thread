"""Test backend."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import Response

from steelthread.offline_evaluators.test_case import OfflineTestCase
from steelthread.online_evaluators.test_case import OnlineTestCase
from steelthread.portia.backend import PortiaBackend
from tests.unit.utils import get_test_config


@pytest.fixture
def backend() -> PortiaBackend:
    """Get backend."""
    return PortiaBackend(config=get_test_config())


def make_response(status_code: int = 200, json_data: object | None = None) -> MagicMock:
    """Make a fake response."""
    mock_response = MagicMock(spec=Response)
    mock_response.is_success = status_code < 400
    mock_response.status_code = status_code
    mock_response.content = b'{"error": "bad"}'
    mock_response.json.return_value = json_data or []
    return mock_response


@patch("steelthread.portia.backend.PortiaCloudClient")
def test_client_returns_httpx_client(mock_portia_client: MagicMock, backend: PortiaBackend) -> None:
    """Check client returns client."""
    mock_client = MagicMock()
    mock_portia_client.return_value.get_client.return_value = mock_client

    client = backend.client()

    mock_portia_client.return_value.get_client.assert_called_once_with(backend.config)
    assert client == mock_client


def test_check_response_success(backend: PortiaBackend) -> None:
    """Check response 200."""
    response = make_response(status_code=200)
    backend.check_response(response)  # should not raise


def test_check_response_failure_raises(backend: PortiaBackend) -> None:
    """Check response 500."""
    response = make_response(status_code=500)
    with pytest.raises(ValueError, match="bad"):
        backend.check_response(response)


@patch.object(PortiaBackend, "client")
def test_load_online_evals(client_mock: MagicMock, backend: PortiaBackend) -> None:
    """Check load evals."""
    client = MagicMock()
    response = make_response(
        json_data=[{"id": "abc", "related_item_id": "123", "related_item_type": "plan"}]
    )
    client.get.return_value = response
    client_mock.return_value = client

    cases = backend.load_online_evals("test-dataset")

    client.get.assert_called_once_with(url="/api/v0/evals/test-cases/?dataset_name=test-dataset")
    assert isinstance(cases[0], OnlineTestCase)


@patch.object(PortiaBackend, "client")
def test_load_offline_evals(client_mock: MagicMock, backend: PortiaBackend) -> None:
    """Check load offline."""
    client = MagicMock()
    response = make_response(
        json_data=[
            {
                "id": "abc",
                "input_config": {"type": "query", "value": "do a backflip."},
                "assertions": [],
            }
        ]
    )
    client.get.return_value = response
    client_mock.return_value = client

    cases = backend.load_offline_evals("test-dataset")

    client.get.assert_called_once_with(url="/api/v0/evals/test-cases/?dataset_name=test-dataset")
    assert isinstance(cases[0], OfflineTestCase)


@patch.object(PortiaBackend, "client")
def test_mark_processed_calls_patch(client_mock: MagicMock, backend: PortiaBackend) -> None:
    """Check processed."""
    client = MagicMock()
    response = make_response()
    client.patch.return_value = response
    client_mock.return_value = client

    tc = OnlineTestCase(id="123", related_item_id="", related_item_type="123")

    backend.mark_processed(tc)

    client.patch.assert_called_once_with(
        url="/api/v0/evals/test-cases/",
        json={"processed": True, "id": "123"},
    )
