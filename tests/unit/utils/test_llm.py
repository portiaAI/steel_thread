"""Test LLM."""

from unittest.mock import MagicMock

import pytest
from _pytest.monkeypatch import MonkeyPatch
from portia import Message

from steelthread.utils.llm import (
    LLMScorer,
    MetricOnly,
    MetricOnlyList,
)


def test_metric_only_valid() -> None:
    """Test metric only."""
    metric = MetricOnly(
        score=0.8,
        name="accuracy",
        description="Measures how accurate the output is.",
        explanation="The output closely matches the expected result.",
    )
    assert metric.score == 0.8
    assert metric.name == "accuracy"


def test_metric_only_invalid_explanation() -> None:
    """Test invalid explanation."""
    with pytest.raises(ValueError, match="explanation must be at least 10 characters"):
        MetricOnly(
            score=0.8,
            name="accuracy",
            description="Measures accuracy",
            explanation="Too short",
        )


def test_metric_only_allows_none_explanation() -> None:
    """Test none explanation."""
    metric = MetricOnly(
        score=1.0,
        name="completeness",
        description="Measures if all parts are included",
        explanation=None,
    )
    assert metric.explanation is None


def test_metric_only_list() -> None:
    """Test metric only list."""
    m1 = MetricOnly(
        score=0.9,
        name="clarity",
        description="Clear writing",
        explanation="Very clear and concise.",
    )
    m2 = MetricOnly(
        score=0.7, name="depth", description="In-depth analysis", explanation="Covers most points."
    )
    metrics_list = MetricOnlyList(metrics=[m1, m2])
    assert len(metrics_list.metrics) == 2


def test_llm_metric_scorer_score(monkeypatch: MonkeyPatch) -> None:  # noqa: ARG001
    """Test metric scorer."""
    # Create mock response from the model
    mock_metrics = [
        MetricOnly(
            score=0.95,
            name="coherence",
            description="Measures logical flow",
            explanation="The output was logically consistent throughout.",
        )
    ]
    mock_response = MetricOnlyList(metrics=mock_metrics)

    mock_model = MagicMock()
    mock_model.get_structured_response.return_value = mock_response

    mock_config = MagicMock()
    mock_config.get_default_model.return_value = mock_model

    scorer = LLMScorer(config=mock_config)

    task_data = ["Step 1: Do X", "Step 2: Do Y"]
    metrics_to_score = [
        MetricOnly(
            score=0.0, name="coherence", description="Measures logical flow", explanation=None
        )
    ]

    result = scorer.score(task_data, metrics_to_score)

    # Ensure correct calls
    mock_model.get_structured_response.assert_called_once()
    assert result == mock_metrics

    # Ensure messages are built as expected
    called_args = mock_model.get_structured_response.call_args[0]
    messages, model_type = called_args
    assert isinstance(messages, list)
    assert isinstance(messages[0], Message)
    assert model_type == MetricOnlyList
