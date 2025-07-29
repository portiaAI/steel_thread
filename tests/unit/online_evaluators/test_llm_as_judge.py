"""LLM as Judge test."""

from unittest.mock import MagicMock, patch

from steelthread.metrics.metric import Metric
from steelthread.online_evaluators.llm_as_judge import LLMJudgeOnlineEvaluator
from tests.unit.utils import get_test_plan_run


@patch("steelthread.online_evaluators.llm_as_judge.LLMMetricScorer")
def test_eval_plan_uses_llm(mock_scorer_class: MagicMock) -> None:
    """Test eval plan via llm."""
    mock_scorer = MagicMock()
    mock_scorer.score.return_value = [
        Metric(name="dummy", description="desc", score=1.0),
        Metric(name="other", description="desc", score=0.5),
    ]
    mock_scorer_class.return_value = mock_scorer

    evaluator = LLMJudgeOnlineEvaluator(config=MagicMock())
    plan, _ = get_test_plan_run()

    result = evaluator.eval_plan(plan)
    assert result == [
        Metric(name="dummy", description="desc", score=1.0),
        Metric(name="other", description="desc", score=0.5),
    ]
    mock_scorer.score.assert_called_once()
    args, kwargs = mock_scorer.score.call_args
    assert "correctness" in [m.name for m in kwargs["metrics_to_score"]]


@patch("steelthread.online_evaluators.llm_as_judge.LLMMetricScorer")
def test_eval_plan_run_uses_llm(mock_scorer_class: MagicMock) -> None:
    """Test eval plan_run via llm."""
    mock_scorer = MagicMock()
    mock_scorer.score.return_value = [
        Metric(name="dummy", description="desc", score=1.0),
        Metric(name="other", description="desc", score=0.5),
    ]
    mock_scorer_class.return_value = mock_scorer

    evaluator = LLMJudgeOnlineEvaluator(config=MagicMock())
    _, plan_run = get_test_plan_run()
    result = evaluator.eval_plan_run(plan_run)

    assert result == [
        Metric(name="dummy", description="desc", score=1.0),
        Metric(name="other", description="desc", score=0.5),
    ]
    mock_scorer.score.assert_called_once()
    args, kwargs = mock_scorer.score.call_args
    assert "success" in [m.name for m in kwargs["metrics_to_score"]]
