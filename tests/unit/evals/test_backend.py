"""Test backend."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from steelthread.evals.backend import PortiaBackend
from steelthread.evals.models import EvalTestCase
from tests.unit.utils import get_test_config


@patch("steelthread.evals.backend.PortiaCloudClient.get_client")
def test_load_evals_pagination(mock_get_client: httpx.Client) -> None:
    """Test loading paginated test cases from the Portia API."""
    config = get_test_config()
    backend = PortiaBackend(config=config)

    # First page response
    page_1 = {
        "results": [
            {
                "id": "tc1",
                "dataset": "myset",
                "input_config": {"type": "query", "value": "hello"},
                "assertions": [],
            }
        ],
        "next": "/api/v0/evals/dataset-test-cases/?page=2",
    }

    # Second page response
    page_2 = {
        "results": [
            {
                "id": "tc2",
                "dataset": "myset",
                "input_config": {"type": "query", "value": "world"},
                "assertions": [],
            }
        ],
        "next": None,
    }

    # Mock client.get() response chain
    mock_client = MagicMock()
    mock_client.get.side_effect = [
        MagicMock(is_success=True, json=MagicMock(return_value=page_1)),
        MagicMock(is_success=True, json=MagicMock(return_value=page_2)),
    ]
    mock_get_client.return_value = mock_client  # type: ignore  # noqa: PGH003

    test_cases = backend.load_evals(dataset_name="myset", run_id="run-123")

    assert len(test_cases) == 2
    assert isinstance(test_cases[0], EvalTestCase)
    assert test_cases[0].testcase == "tc1"
    assert test_cases[0].run == "run-123"
    assert test_cases[1].testcase == "tc2"
    assert test_cases[1].input_config.value == "world"

    # Ensure pagination happened
    assert mock_client.get.call_count == 2
    mock_get_client.assert_called_once_with(config)  # type: ignore  # noqa: PGH003


def test_check_response_raises_on_error() -> None:
    """Test that check_response raises ValueError for non-success response."""
    backend = PortiaBackend(config=get_test_config())

    # Simulate an error response
    response = httpx.Response(status_code=400, content=b'{"detail": "Bad request"}')

    with pytest.raises(ValueError, match="Bad request"):
        backend.check_response(response)
