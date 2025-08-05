"""Test LLMasJudge."""

from unittest.mock import MagicMock, patch

import pytest

from steelthread.streams.llm_as_judge import LLMJudgeOnlineEvaluator
from steelthread.streams.metrics import StreamMetric
from steelthread.streams.models import PlanRunStreamItem, PlanStreamItem
from steelthread.utils.llm import MetricOnly
from tests.unit.utils import get_test_config, get_test_plan_run


@pytest.fixture
def mock_metrics() -> list[MetricOnly]:
    """Fixture for mocked LLM metrics."""
    return [
        MetricOnly(score=0.9, name="test_metric", description="A test", explanation="Test passed.")
    ]


@patch("steelthread.streams.llm_as_judge.LLMMetricScorer")
def test_process_plan_returns_metrics(
    mock_scorer_cls: MagicMock,
    mock_metrics: list[MetricOnly],
) -> None:
    """Test that process_plan returns scored metrics."""
    mock_scorer = MagicMock()
    mock_scorer.score.return_value = mock_metrics
    mock_scorer_cls.return_value = mock_scorer

    evaluator = LLMJudgeOnlineEvaluator(config=get_test_config())
    plan, _ = get_test_plan_run()
    stream_item = PlanStreamItem(stream="s1", stream_item="i1", plan=plan)

    result = evaluator.process_plan(stream_item)
    assert isinstance(result, list)
    assert isinstance(result[0], StreamMetric)
    assert result[0].name == "test_metric"
    mock_scorer.score.assert_called_once()


@patch("steelthread.streams.llm_as_judge.LLMMetricScorer")
def test_process_plan_run_returns_metrics(
    mock_scorer_cls: MagicMock,
    mock_metrics: list[MetricOnly],
) -> None:
    """Test that process_plan_run returns scored metrics."""
    mock_scorer = MagicMock()
    mock_scorer.score.return_value = mock_metrics
    mock_scorer_cls.return_value = mock_scorer

    evaluator = LLMJudgeOnlineEvaluator(config=get_test_config())
    plan, plan_run = get_test_plan_run()
    stream_item = PlanRunStreamItem(stream="s1", stream_item="i2", plan=plan, plan_run=plan_run)

    result = evaluator.process_plan_run(stream_item)
    assert isinstance(result, list)
    assert isinstance(result[0], StreamMetric)
    assert result[0].name == "test_metric"
    mock_scorer.score.assert_called_once()
