"""Test metrics backend."""

import pytest

from steelthread.common.models import EvalRun
from steelthread.metrics.metric import (
    LogMetricBackend,
    Metric,
    MetricsBackend,
    MetricTagger,
    MetricWithTag,
)
from tests.unit.utils import get_test_config


def test_log_metric_backend_saves_metrics(capfd: pytest.CaptureFixture[str]) -> None:
    """Test backend logs correctly."""
    backend = LogMetricBackend()

    metrics = [
        MetricWithTag(name="accuracy", description="", score=0.9, tags={"task": "A", "phase": "1"}),
        MetricWithTag(name="accuracy", description="", score=0.8, tags={"task": "A", "phase": "1"}),
        MetricWithTag(name="clarity", description="", score=0.95, tags={"task": "B", "phase": "2"}),
    ]

    backend.save_metrics(EvalRun(data_set_name="", data_set_type=""), metrics)

    out, _ = capfd.readouterr()

    assert "=== Metric Averages ===" in out
    assert "accuracy" in out
    assert "clarity" in out
    assert "task" in out
    assert "phase" in out
    assert "0.85" in out  # mean of 0.9 and 0.8


def test_metric_base_classes() -> None:
    """Test metric base class raises."""

    class MyMetricsBackend(MetricsBackend):
        """Override to test base."""

        def save_metrics(self, eval_run: EvalRun, metrics: list[MetricWithTag]) -> None:
            return super().save_metrics(eval_run, metrics)  # type: ignore  # noqa: PGH003

    backend = MyMetricsBackend()  # type: ignore  # noqa: PGH003

    metrics = [
        MetricWithTag(name="accuracy", description="", score=0.9, tags={"task": "A", "phase": "1"}),
        MetricWithTag(name="accuracy", description="", score=0.8, tags={"task": "A", "phase": "1"}),
        MetricWithTag(name="clarity", description="", score=0.95, tags={"task": "B", "phase": "2"}),
    ]

    with pytest.raises(NotImplementedError):
        backend.save_metrics(EvalRun(data_set_name="", data_set_type=""), metrics)


def test_attach_tags() -> None:
    """Test tags are attached."""
    metric = Metric(name="accuracy", description="Test accuracy", score=0.9)
    tags = {"task": "A", "phase": "1"}
    config = get_test_config()
    result = MetricTagger().attach_tags(config, metric, tags)

    expected = MetricWithTag(
        score=0.9,
        name="accuracy",
        description="Test accuracy",
        tags={
            "planning_model": config.get_planning_model().model_name,
            "execution_model": config.get_execution_model().model_name,
            **tags,
        },
    )
    assert result == expected
