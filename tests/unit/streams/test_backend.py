"""Test stream backend."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from httpx import Request, Response

from steelthread.streams.backend import PortiaStreamBackend
from steelthread.streams.models import PlanRunStreamItem, PlanStreamItem, Stream
from tests.unit.utils import get_test_config, get_test_plan_run


@pytest.fixture
def backend() -> PortiaStreamBackend:
    """Fixture for a PortiaStreamBackend instance."""
    return PortiaStreamBackend(config=get_test_config())


def make_mock_response(data: Any, status_code: int = 200) -> Response:  # noqa: ANN401
    """Return an httpx.Response with JSON data."""
    return Response(
        status_code=status_code,
        json=data,
        request=Request("GET", "https://fake.url/api/"),
    )


@patch("steelthread.streams.backend.PortiaCloudClient")
def test_get_stream_success(mock_client_class: MagicMock, backend: PortiaStreamBackend) -> None:
    """Test getting a stream successfully."""
    mock_client = MagicMock()

    mock_response = make_mock_response(
        {
            "id": "abc",
            "name": "my-stream",
            "source": "plan",
            "sample_rate": 100,
            "sample_filters": {},
            "last_sampled": "",
        }
    )
    mock_client.get.return_value = mock_response
    mock_client_class.return_value.new_client.return_value = mock_client

    stream = backend.get_stream("my-stream")
    assert isinstance(stream, Stream)
    assert stream.name == "my-stream"


@patch("steelthread.streams.backend.PortiaCloudClient")
def test_check_response_raises_on_failure(
    mock_client_class: MagicMock,  # noqa: ARG001
    backend: PortiaStreamBackend,
) -> None:
    """Test check_response raises ValueError on error response."""
    response = Response(400, content=b"Bad Request", request=Request("GET", "https://fake.url"))
    with pytest.raises(ValueError, match="Bad Request"):
        backend.check_response(response)


@patch("steelthread.streams.backend.PortiaCloudClient")
def test_load_plan_stream_items_pagination(
    mock_client_class: MagicMock, backend: PortiaStreamBackend
) -> None:
    """Test loading PlanStreamItems with pagination."""
    plan = get_test_plan_run()[0]

    page_1 = {
        "results": [{"id": "item-1", "plan": plan.model_dump()}],
        "current_page": 1,
        "total_pages": 3,
    }

    # Second page response
    page_2 = {
        "results": [{"id": "item-2", "plan": plan.model_dump()}],
        "current_page": 2,
        "total_pages": 3,
    }

    page_3 = {
        "results": [{"id": "item-3", "plan": plan.model_dump()}],
        "current_page": 3,
        "total_pages": 3,
    }

    mock_client = MagicMock()
    mock_client_class.return_value.new_client.return_value = mock_client
    mock_client.get.side_effect = [
        MagicMock(is_success=True, json=MagicMock(return_value=page_1)),
        MagicMock(is_success=True, json=MagicMock(return_value=page_2)),
        MagicMock(is_success=True, json=MagicMock(return_value=page_3)),
    ]
    mock_client.return_value = mock_client  # type: ignore  # noqa: PGH003

    items = backend.load_plan_stream_items("stream-123", batch_size=2)
    assert len(items) == 2
    assert isinstance(items[0], PlanStreamItem)

    mock_client.get.side_effect = [
        MagicMock(is_success=True, json=MagicMock(return_value=page_1)),
        MagicMock(is_success=True, json=MagicMock(return_value=page_2)),
        MagicMock(is_success=True, json=MagicMock(return_value=page_3)),
    ]
    mock_client.return_value = mock_client  # type: ignore  # noqa: PGH003

    items = backend.load_plan_stream_items("stream-123", batch_size=3)
    assert len(items) == 3
    assert isinstance(items[0], PlanStreamItem)


@patch("steelthread.streams.backend.PortiaCloudClient")
def test_load_plan_run_stream_items(
    mock_client_class: MagicMock, backend: PortiaStreamBackend
) -> None:
    """Test loading PlanRunStreamItems."""
    mock_client = MagicMock()
    mock_client_class.return_value.new_client.return_value = mock_client

    plan, plan_run = get_test_plan_run()
    page_1 = {
        "results": [
            {
                "id": "item-1",
                "plan": {
                    "id": str(plan_run.plan_id),
                    "query": plan.plan_context.query,
                    "tool_ids": plan.plan_context.tool_ids,
                    "steps": [s.model_dump() for s in plan.steps],
                    "plan_inputs": plan.plan_inputs,
                },
                "plan_run": {
                    "id": str(plan_run.id),
                    "plan": {
                        "id": str(plan_run.plan_id),
                        "query": plan.plan_context.query,
                        "tool_ids": plan.plan_context.tool_ids,
                        "steps": [s.model_dump() for s in plan.steps],
                        "plan_inputs": plan.plan_inputs,
                    },
                    "end_user": plan_run.end_user_id,
                    "current_step_index": plan_run.current_step_index,
                    "state": plan_run.state.value,
                    "outputs": plan_run.outputs.model_dump(),
                    "plan_run_inputs": {
                        k: v.model_dump() for k, v in plan_run.plan_run_inputs.items()
                    },
                },
            }
        ],
        "current_page": 1,
        "total_pages": 3,
    }
    page_2 = {
        "results": [
            {
                "id": "item-2",
                "plan": {
                    "id": str(plan_run.plan_id),
                    "query": plan.plan_context.query,
                    "tool_ids": plan.plan_context.tool_ids,
                    "steps": [s.model_dump() for s in plan.steps],
                    "plan_inputs": plan.plan_inputs,
                },
                "plan_run": {
                    "id": str(plan_run.id),
                    "plan": {
                        "id": str(plan_run.plan_id),
                        "query": plan.plan_context.query,
                        "tool_ids": plan.plan_context.tool_ids,
                        "steps": [s.model_dump() for s in plan.steps],
                        "plan_inputs": plan.plan_inputs,
                    },
                    "end_user": plan_run.end_user_id,
                    "current_step_index": plan_run.current_step_index,
                    "state": plan_run.state.value,
                    "outputs": plan_run.outputs.model_dump(),
                    "plan_run_inputs": {
                        k: v.model_dump() for k, v in plan_run.plan_run_inputs.items()
                    },
                },
            }
        ],
        "current_page": 2,
        "total_pages": 3,
    }
    page_3 = {
        "results": [
            {
                "id": "item-2",
                "plan": {
                    "id": str(plan_run.plan_id),
                    "query": plan.plan_context.query,
                    "tool_ids": plan.plan_context.tool_ids,
                    "steps": [s.model_dump() for s in plan.steps],
                    "plan_inputs": plan.plan_inputs,
                },
                "plan_run": {
                    "id": str(plan_run.id),
                    "plan": {
                        "id": str(plan_run.plan_id),
                        "query": plan.plan_context.query,
                        "tool_ids": plan.plan_context.tool_ids,
                        "steps": [s.model_dump() for s in plan.steps],
                        "plan_inputs": plan.plan_inputs,
                    },
                    "end_user": plan_run.end_user_id,
                    "current_step_index": plan_run.current_step_index,
                    "state": plan_run.state.value,
                    "outputs": plan_run.outputs.model_dump(),
                    "plan_run_inputs": {
                        k: v.model_dump() for k, v in plan_run.plan_run_inputs.items()
                    },
                },
            }
        ],
        "current_page": 3,
        "total_pages": 3,
    }
    mock_client.get.side_effect = [
        MagicMock(is_success=True, json=MagicMock(return_value=page_1)),
        MagicMock(is_success=True, json=MagicMock(return_value=page_2)),
        MagicMock(is_success=True, json=MagicMock(return_value=page_3)),
    ]
    mock_client.return_value = mock_client  # type: ignore  # noqa: PGH003

    items = backend.load_plan_run_stream_items("stream-123", batch_size=2)
    assert len(items) == 2
    assert isinstance(items[0], PlanRunStreamItem)

    mock_client.get.side_effect = [
        MagicMock(is_success=True, json=MagicMock(return_value=page_1)),
        MagicMock(is_success=True, json=MagicMock(return_value=page_2)),
        MagicMock(is_success=True, json=MagicMock(return_value=page_3)),
    ]
    mock_client.return_value = mock_client  # type: ignore  # noqa: PGH003

    items = backend.load_plan_run_stream_items("stream-123", batch_size=3)
    assert len(items) == 3
    assert isinstance(items[0], PlanRunStreamItem)


@patch("steelthread.streams.backend.PortiaCloudClient")
def test_mark_processed_calls_patch(
    mock_client_class: MagicMock, backend: PortiaStreamBackend
) -> None:
    """Test mark_processed makes a PATCH request."""
    mock_client = MagicMock()
    mock_client_class.return_value.new_client.return_value = mock_client
    mock_response = make_mock_response({}, 200)
    mock_client.patch.return_value = mock_response

    plan, _ = get_test_plan_run()
    item = PlanStreamItem(stream="stream-123", stream_item="item-456", plan=plan)
    backend.mark_processed(item)

    mock_client.patch.assert_called_once()
    assert mock_client.patch.call_args[1]["json"]["id"] == "item-456"


@patch("steelthread.streams.backend.PortiaCloudClient")
def test_load_plan_run_stream_items_no_results(
    mock_client_class: MagicMock, backend: PortiaStreamBackend
) -> None:
    """Test load_plan_stream_items returns empty list if no results."""
    mock_client = MagicMock()
    mock_client_class.return_value.new_client.return_value = mock_client
    mock_response = make_mock_response({"results": []}, 200)
    mock_client.get.return_value = mock_response

    items = backend.load_plan_run_stream_items("stream-123", batch_size=2)
    assert len(items) == 0


@patch("steelthread.streams.backend.PortiaCloudClient")
def test_load_plan_stream_items_items_no_results(
    mock_client_class: MagicMock, backend: PortiaStreamBackend
) -> None:
    """Test load_plan_stream_items returns empty list if no results."""
    mock_client = MagicMock()
    mock_client_class.return_value.new_client.return_value = mock_client
    mock_response = make_mock_response({"results": []}, 200)
    mock_client.get.return_value = mock_response

    items = backend.load_plan_stream_items("stream-123", batch_size=2)
    assert len(items) == 0
