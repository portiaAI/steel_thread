"""Metrics backend."""

from abc import ABC, abstractmethod

import httpx
import pandas as pd
from portia.config import Config
from portia.storage import PortiaCloudClient
from pydantic import BaseModel, Field, field_serializer, field_validator

from steelthread.evals.models import EvalTestCase

MIN_EXPLANATION_LENGTH = 10


class EvalMetric(BaseModel):
    """A single record of an observation.

    Attributes:
        dataset (str): the id of the dataset.
        testcase (str): the id of the testcase.
        run (str): the id of the run
        score (float): The numeric value of the metric.
        name (str): The name of the metric.
        expectation (str | list[str] | dict[str, str] | None): expected value
        actual_value (str | list[str] | dict[str, str] | None): actual value
        description (str): A human-readable description of the metric.
        explanation (str | None): An optional explanation of the score.
        tags (dict[str, str]): A set of tags to query this metric by.

    """

    dataset: str
    testcase: str
    run: str
    score: float
    name: str
    description: str
    expectation: str | list[str] | dict[str, str] | None
    actual_value: str | list[str] | dict[str, str] | None
    eval_output: dict[str, BaseModel] | None = Field(
        default=None,
        description="The Plan or PlanRun that was used to generate the metric.",
    )
    explanation: str | None = Field(default="", description="An optional explanation of the score.")
    tags: dict[str, str] = Field(default={})

    @field_validator("explanation")
    @classmethod
    def explanation_min_length(cls, v: str | None) -> str | None:
        """If an explanation is provided it must have length."""
        if v is not None and len(v) < MIN_EXPLANATION_LENGTH:
            raise ValueError("explanation must be at least 5 characters long")
        return v

    @field_serializer("eval_output")
    def serialize_eval_output(self, v: dict[str, BaseModel] | None) -> dict:
        """Serialize the eval output to a dictionary of strings."""
        return {k: v.model_dump() for k, v in v.items()} if v else {}

    @classmethod
    def from_test_case(
        cls,
        test_case: EvalTestCase,
        score: float,
        name: str,
        description: str,
        explanation: str | None = None,
        expectation: str | list[str] | dict[str, str] | None = None,
        actual_value: str | list[str] | dict[str, str] | None = None,
        eval_output: dict[str, BaseModel] | None = None,
    ) -> "EvalMetric":
        """Create a metric from a test case.

        Args:
            test_case (EvalTestCase): The test case this metric relates to
            score (float): The numeric value of the metric.
            name (str): The name of the metric.
            description (str): A human-readable description of the metric.
            explanation (str | None): An optional explanation of the score.
            expectation (str | list[str] | dict[str, str] | None): expected value
            actual_value (str | list[str] | dict[str, str] | None): actual value
            eval_output (dict[str, BaseModel] | None): The output of the eval run.

        """
        return cls(
            dataset=test_case.dataset,
            testcase=test_case.testcase,
            run=test_case.run,
            score=score,
            name=name,
            description=description,
            explanation=explanation,
            actual_value=actual_value,
            eval_output=eval_output,
            expectation=expectation,
        )


class MetricsBackend(ABC):
    """Abstract interface for saving metrics."""

    @abstractmethod
    def save_eval_metrics(self, metrics: list[EvalMetric]) -> None:
        """Save a list of tagged metrics for a specific evaluation run.

        Args:
            eval_run (EvalRun): The evaluation run context.
            metrics (list[MetricWithTag]): The metrics to save.

        """
        raise NotImplementedError


class PortiaEvalMetricsBackend(MetricsBackend):
    """Backend for saving metrics to the Portia API."""

    def __init__(self, config: Config) -> None:
        """Init config."""
        self.config = config

    def client(self) -> httpx.Client:
        """Return an authenticated HTTP client."""
        return PortiaCloudClient(self.config).new_client(self.config)

    def check_response(self, response: httpx.Response) -> None:
        """Raise if response is not successful."""
        if not response.is_success:
            raise ValueError(f"Portia API error: {response.status_code} - {response.text}")

    def save_eval_metrics(self, metrics: list[EvalMetric]) -> None:
        """Send metrics to the Portia API for a given eval run."""
        payload = [m.model_dump() for m in metrics]
        client = self.client()
        response = client.post("/api/v0/evals/eval-metrics/", json=payload)
        self.check_response(response)


class EvalLogMetricBackend(MetricsBackend):
    """Implementation of the metrics backend that logs scores.

    This backend prints average metric scores grouped by name and tags.
    """

    def save_eval_metrics(self, metrics: list[EvalMetric]) -> None:
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
