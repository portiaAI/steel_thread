"""Test metrics."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import Request, Response

from steelthread.evals.metrics import (
    EvalLogMetricBackend,
    EvalMetric,
    MetricsBackend,
    PortiaEvalMetricsBackend,
)
from steelthread.evals.models import EvalTestCase, InputConfig
from tests.unit.utils import get_test_config


@pytest.fixture
def test_case() -> EvalTestCase:
    """Fixture for a sample EvalTestCase."""
    return EvalTestCase(
        dataset="ds1",
        testcase="tc1",
        run="run1",
        input_config=InputConfig(type="query", value="test input"),
        assertions=[],
    )


def test_eval_metric_from_test_case(test_case: EvalTestCase) -> None:
    """Test EvalMetric.from_test_case builds correct metric."""
    metric = EvalMetric.from_test_case(
        test_case=test_case,
        score=0.9,
        name="accuracy",
        description="Test accuracy",
        explanation="Looks good",
        expectation="yes",
        actual_value="yes",
    )
    assert metric.dataset == "ds1"
    assert metric.score == 0.9
    assert metric.explanation == "Looks good"
    assert metric.name == "accuracy"
    assert metric.expectation == "yes"
    assert metric.actual_value == "yes"


def test_eval_metric_explanation_too_short() -> None:
    """Test EvalMetric explanation validation fails for short input."""
    with pytest.raises(ValueError, match="explanation must be at least 5 characters"):
        EvalMetric(
            dataset="d",
            testcase="t",
            run="r",
            score=1.0,
            name="clarity",
            description="desc",
            explanation="bad",
            expectation="x",
            actual_value="y",
        )


def test_metrics_backend_abstract_class() -> None:
    """Test base MetricsBackend class raises NotImplementedError."""

    class DummyBackend(MetricsBackend):
        def save_eval_metrics(self, metrics: list[EvalMetric]) -> None:
            return super().save_eval_metrics(metrics)  # type: ignore  # noqa: PGH003

    backend = DummyBackend()
    with pytest.raises(NotImplementedError):
        backend.save_eval_metrics([])


@patch("steelthread.evals.metrics.PortiaCloudClient")
def test_portia_eval_metrics_backend_success(mock_client_class: MagicMock) -> None:
    """Test PortiaEvalMetricsBackend saves metrics via HTTP."""
    config = get_test_config()
    backend = PortiaEvalMetricsBackend(config)

    metric = EvalMetric(
        dataset="d",
        testcase="t",
        run="r",
        score=1.0,
        name="accuracy",
        description="desc",
        explanation="explanation passed",
        expectation="yes",
        actual_value="yes",
    )

    mock_client = MagicMock()
    mock_response = Response(
        status_code=200,
        json={},
        request=Request("POST", "https://api.fake/"),
    )
    mock_client.post.return_value = mock_response
    mock_client_class.return_value.get_client.return_value = mock_client

    backend.save_eval_metrics([metric])
    mock_client.post.assert_called_once()
    call = mock_client.post.call_args[1]
    assert isinstance(call["json"], list)
    assert call["json"][0]["name"] == "accuracy"


@patch("steelthread.evals.metrics.PortiaCloudClient")
def test_portia_eval_metrics_backend_failure(mock_client_class: MagicMock) -> None:
    """Test PortiaEvalMetricsBackend raises error on failed API call."""
    config = get_test_config()
    backend = PortiaEvalMetricsBackend(config)

    metric = EvalMetric(
        dataset="d",
        testcase="t",
        run="r",
        score=0.8,
        name="clarity",
        description="desc",
        explanation="good enough",
        expectation="yes",
        actual_value="no",
    )

    mock_client = MagicMock()
    mock_response = Response(
        status_code=500,
        text="Internal Server Error",
        request=Request("POST", "https://api.fake/"),
    )
    mock_client.post.return_value = mock_response
    mock_client_class.return_value.get_client.return_value = mock_client

    with pytest.raises(ValueError, match="Portia API error: 500"):
        backend.save_eval_metrics([metric])


def test_eval_log_metric_backend_outputs(capfd: pytest.CaptureFixture) -> None:
    """Test EvalLogMetricBackend prints aggregated output."""
    backend = EvalLogMetricBackend()

    metrics = [
        EvalMetric(
            dataset="d",
            testcase="t1",
            run="r",
            score=0.9,
            name="clarity",
            description="desc",
            explanation="clear explanation",
            expectation="yes",
            actual_value="yes",
            tags={"env": "test"},
        ),
        EvalMetric(
            dataset="d",
            testcase="t2",
            run="r",
            score=0.6,
            name="clarity",
            description="desc",
            explanation="less clear",
            expectation="yes",
            actual_value="no",
            tags={"env": "test"},
        ),
    ]

    backend.save_eval_metrics(metrics)

    out, _ = capfd.readouterr()
    assert "=== Metric Averages ===" in out
    assert "clarity" in out
    assert "0.75" in out or "0.749" in out  # Average of 0.9 and 0.6
