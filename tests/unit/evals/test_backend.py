"""Test backend."""

import httpx
import pytest
from portia import Config
from pytest_httpx import HTTPXMock

from steelthread.evals.backend import PortiaBackend
from steelthread.evals.models import EvalTestCase
from tests.unit.utils import get_test_config


@pytest.fixture
def config() -> Config:
    """Fixture for a Portia config."""
    return get_test_config()


@pytest.fixture
def backend(config: Config) -> PortiaBackend:
    """Fixture for a PortiaBackend."""
    return PortiaBackend(config=config)


def test_load_evals_pagination(backend: PortiaBackend, httpx_mock: HTTPXMock) -> None:
    """Test loading paginated test cases from the Portia API."""
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
        "current_page": 1,
        "total_pages": 2,
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
        "current_page": 2,
        "total_pages": 2,
    }

    # Mock the HTTP responses using pytest-httpx
    httpx_mock.add_response(
        url=f"{backend.config.portia_api_endpoint}/api/v0/evals/dataset-test-cases/?dataset_name=myset&page=1",
        json=page_1,
        status_code=200,
    )
    httpx_mock.add_response(
        url=f"{backend.config.portia_api_endpoint}/api/v0/evals/dataset-test-cases/?dataset_name=myset&page=2",
        json=page_2,
        status_code=200,
    )

    test_cases = backend.load_evals(dataset_name="myset", run_id="run-123")

    assert len(test_cases) == 2
    assert isinstance(test_cases[0], EvalTestCase)
    assert test_cases[0].testcase == "tc1"
    assert test_cases[0].run == "run-123"
    assert test_cases[1].testcase == "tc2"
    assert test_cases[1].input_config.value == "world"

    # Verify that both requests were made
    assert len(httpx_mock.get_requests()) == 2


def test_check_response_raises_on_error(backend: PortiaBackend) -> None:
    """Test that check_response raises ValueError for non-success response."""
    # Simulate an error response
    response = httpx.Response(status_code=400, content=b'{"detail": "Bad request"}')

    with pytest.raises(ValueError, match="Bad request"):
        backend.check_response(response)
