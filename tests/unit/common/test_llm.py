"""Tests for LLM judge."""

from typing import TypeVar

from portia import Config, LLMProvider, Message
from pydantic import BaseModel, SecretStr

from steelthread.utils.llm import (
    LLMMetricScorer,
)
from steelthread.tags.offline_metric import Metric, MetricList

BaseModelT = TypeVar("BaseModelT", bound=BaseModel)


class MockConfig(Config):
    """Mock Config class."""

    def get_default_model(self):  # type: ignore  # noqa: ANN201, PGH003
        """Return self."""
        return self

    def get_structured_response(
        self,
        _: list[Message],
        schema: type[BaseModelT],
    ) -> MetricList:
        """Return hardcoded metrics."""
        assert issubclass(schema, MetricList)
        return MetricList(
            metrics=[
                Metric(
                    name="accuracy",
                    description="How accurate the response was",
                    score=0.95,
                    explanation="Very accurate result.",
                ),
                Metric(
                    name="clarity",
                    description="How clear the response was",
                    score=0.9,
                    explanation="Clear and understandable.",
                ),
            ]
        )


def test_llm_metric_scorer_returns_scored_metrics() -> None:
    """Check correct metrics are returned."""
    scorer = LLMMetricScorer(
        config=MockConfig(openai_api_key=SecretStr("123"), llm_provider=LLMProvider.OPENAI)
    )

    task_data = ["Task: Summarize this article", "Output: The article is about AI."]
    metrics_to_score = [
        Metric(name="accuracy", description="How accurate the response was", score=0.0),
        Metric(name="clarity", description="How clear the response was", score=0.0),
    ]

    result = scorer.score(task_data, metrics_to_score)

    assert isinstance(result, list)
    assert all(isinstance(m, Metric) for m in result)
    assert [m.name for m in result] == ["accuracy", "clarity"]
    assert [m.score for m in result] == [0.95, 0.9]
