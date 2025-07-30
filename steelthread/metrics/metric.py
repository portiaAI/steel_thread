"""Metrics."""

from abc import ABC, abstractmethod

import pandas as pd
from portia import Config
from pydantic import BaseModel, Field, field_validator

from steelthread.common.models import EvalRun

MIN_EXPLANATION_LENGTH = 10


class Metric(BaseModel):
    """A single record of an observation.

    Attributes:
        score (float): The numeric value of the metric.
        name (str): The name of the metric.
        description (str): A human-readable description of the metric.

    """

    score: float
    name: str
    description: str
    explanation: str | None = Field(
        default=None, description="An optional explanation of the score."
    )

    @field_validator("explanation")
    @classmethod
    def explanation_min_length(cls, v: str | None) -> str | None:
        """If an explanation is provided it must have length."""
        if v is not None and len(v) < MIN_EXPLANATION_LENGTH:
            raise ValueError("explanation must be at least 5 characters long")
        return v


class MetricWithTag(BaseModel):
    """A metric along with a set of tags.

    Attributes:
        score (float): The numeric value of the metric.
        name (str): The name of the metric.
        description (str): A human-readable description of the metric.
        tags (dict[str, str]): Key-value pairs describing metadata (e.g., model names).
        explanation (str | None): An optional explanation of why this score is such.

    """

    score: float
    name: str
    description: str
    tags: dict[str, str]
    explanation: str | None = None


class MetricList(BaseModel):
    """A list of metrics.

    Attributes:
        metrics (list[Metric]): A collection of individual metrics.

    """

    metrics: list[Metric]


class MetricsBackend(ABC):
    """Abstract interface for saving metrics."""

    @abstractmethod
    def save_metrics(self, eval_run: EvalRun, metrics: list[MetricWithTag]) -> None:
        """Save a list of tagged metrics for a specific evaluation run.

        Args:
            eval_run (EvalRun): The evaluation run context.
            metrics (list[MetricWithTag]): The metrics to save.

        """
        raise NotImplementedError


class LogMetricBackend(MetricsBackend):
    """Implementation of the metrics backend that logs scores.

    This backend prints average metric scores grouped by name and tags.
    """

    def save_metrics(self, eval_run: EvalRun, metrics: list[MetricWithTag]) -> None:  # noqa: ARG002
        """Log metrics via pandas.

        Converts the metrics list into a DataFrame, expands tags into columns,
        groups by metric name and tag combinations, and prints average scores.

        Args:
            eval_run (EvalRun): The evaluation run context (unused).
            metrics (list[MetricWithTag]): The metrics to log.

        """
        # Convert list of metrics to DataFrame
        dataframe = pd.DataFrame([m.model_dump() for m in metrics])

        # Expand the 'tags' column into separate columns
        tags_df = dataframe["tags"].apply(pd.Series)
        dataframe = pd.concat([dataframe.drop(columns=["tags"]), tags_df], axis=1)

        # Determine which columns to group by: metric name + all tag columns
        group_keys = ["name", *tags_df.columns.tolist()]

        # Group by name + tags, then compute mean score
        avg_scores = dataframe.groupby(group_keys)["score"].mean().reset_index()

        # Print
        print("\n=== Metric Averages ===")  # noqa: T201
        print(avg_scores.to_string(index=False))  # noqa: T201


class MetricTagger:
    """Class for attaching tags to metrics."""

    @staticmethod
    def attach_tags(
        config: Config,
        metric: Metric,
        additional_tags: dict[str, str] | None = None,
    ) -> MetricWithTag:
        """Attach configuration-based and additional tags to a metric.

        Args:
            config (Config): Configuration object providing model names.
            metric (Metric): The original metric to tag.
            additional_tags (dict[str, str] | None): Extra tags to include (optional).

        Returns:
            MetricWithTag: The metric augmented with tags.

        """
        return MetricWithTag(
            score=metric.score,
            name=metric.name,
            description=metric.description,
            tags={
                "planning_model": config.get_planning_model().model_name,
                "execution_model": config.get_execution_model().model_name,
                **(additional_tags or {}),
            },
        )
