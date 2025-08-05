"""Test metrics."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import Request, Response

from steelthread.streams.metrics import (
    PortiaStreamMetricsBackend,
    StreamLogMetricBackend,
    StreamMetric,
    StreamMetricsBackend,
)
from steelthread.streams.models import PlanStreamItem
from tests.unit.utils import get_test_config, get_test_plan_run


def test_stream_metric_from_stream_item() -> None:
    """Test creating a StreamMetric from a stream item."""
    plan, _ = get_test_plan_run()
    item = PlanStreamItem(stream="stream-123", stream_item="item-456", plan=plan)

    metric = StreamMetric.from_stream_item(
        stream_item=item,
        score=1.0,
        name="clarity",
        description="Clarity of output.",
        explanation="Very clear output.",
    )

    assert metric.stream == "stream-123"
    assert metric.name == "clarity"
    assert metric.explanation == "Very clear output."


def test_stream_metric_explanation_too_short() -> None:
    """Test explanation validation fails on short text."""
    with pytest.raises(ValueError, match="explanation must be at least 5 characters long"):
        StreamMetric(
            stream="s",
            stream_item="i",
            score=1.0,
            name="test",
            description="desc",
            explanation="bad",
        )


def test_stream_metrics_backend_abstract() -> None:
    """Test abstract base class raises NotImplementedError."""

    class DummyBackend(StreamMetricsBackend):
        def save_metrics(self, metrics: list[StreamMetric]) -> None:
            return super().save_metrics(metrics)  # type: ignore  # noqa: PGH003

    backend = DummyBackend()
    with pytest.raises(NotImplementedError):
        backend.save_metrics([])


@patch("steelthread.streams.metrics.PortiaCloudClient")
def test_portia_stream_metrics_backend_success(mock_client_class: MagicMock) -> None:
    """Test PortiaStreamMetricsBackend sends data and handles success."""
    config = get_test_config()
    backend = PortiaStreamMetricsBackend(config)

    metric = StreamMetric(
        stream="s",
        stream_item="i",
        score=0.5,
        name="accuracy",
        description="how accurate",
        explanation="accurate enough",
    )

    mock_client = MagicMock()
    mock_response = Response(
        status_code=200,
        json={},
        request=Request("POST", "https://fake.url/api/v0/evals/stream-metrics/"),
    )
    mock_client.post.return_value = mock_response
    mock_client_class.return_value.get_client.return_value = mock_client

    backend.save_metrics([metric])
    mock_client.post.assert_called_once()


@patch("steelthread.streams.metrics.PortiaCloudClient")
def test_portia_stream_metrics_backend_failure(mock_client_class: MagicMock) -> None:
    """Test PortiaStreamMetricsBackend raises on bad response."""
    config = get_test_config()
    backend = PortiaStreamMetricsBackend(config)

    metric = StreamMetric(
        stream="s",
        stream_item="i",
        score=0.5,
        name="accuracy",
        description="how accurate",
        explanation="accurate enough",
    )

    mock_client = MagicMock()
    mock_response = Response(
        status_code=400,
        text="Invalid",
        request=Request("POST", "https://fake.url"),
    )
    mock_client.post.return_value = mock_response
    mock_client_class.return_value.get_client.return_value = mock_client

    with pytest.raises(ValueError, match="Portia API error: 400"):
        backend.save_metrics([metric])


def test_stream_log_metrics_backend_logs_metrics(capfd: pytest.CaptureFixture) -> None:
    """Test StreamLogMetricBackend prints grouped metrics with averages."""
    backend = StreamLogMetricBackend()

    metric1 = StreamMetric(
        stream="s",
        stream_item="1",
        score=0.9,
        name="success",
        description="",
        explanation="It worked v well",
        tags={"stage": "eval"},
    )

    metric2 = StreamMetric(
        stream="s",
        stream_item="2",
        score=0.6,
        name="success",
        description="",
        explanation="Could be better",
        tags={"stage": "eval"},
    )

    backend.save_metrics([metric1, metric2])
    out, _ = capfd.readouterr()
    assert "=== Metric Averages ===" in out
    assert "success" in out
    assert "0.75" in out or "0.749" in out  # average of 0.9 and 0.6
