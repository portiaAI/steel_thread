"""Stream Metrics."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

import httpx
import pandas as pd
from portia import Config
from portia.storage import PortiaCloudClient
from pydantic import BaseModel, Field, field_validator

MIN_EXPLANATION_LENGTH = 10


class StreamMetric(BaseModel):
    """A single record of an observation.

    Attributes:
        stream_item (UUID): The id of the stream item this metric relates to
        score (float): The numeric value of the metric.
        name (str): The name of the metric.
        description (str): A human-readable description of the metric.
        tags (dict[str, str]): A set of tags to query this metric by.

    """

    stream: str
    stream_item: str
    score: float
    name: str
    description: str
    explanation: str | None = Field(
        default=None,
        description="An optional explanation of the score.",
    )
    tags: dict[str, str] | None = Field(default={}, description="Tags for querying this metric.")

    @field_validator("explanation")
    @classmethod
    def explanation_min_length(cls, v: str | None) -> str | None:
        """If an explanation is provided it must have length."""
        if v is not None and len(v) < MIN_EXPLANATION_LENGTH:
            raise ValueError("explanation must be at least 5 characters long")
        return v


class StreamMetricsBackend(ABC):
    """Abstract interface for saving metrics."""

    @abstractmethod
    def save_metrics(self, metrics: list[StreamMetric]) -> None:
        """Save a list of tagged metrics for a specific evaluation run.

        Args:
            metrics (list[StreamMetricWithTags]): The metrics to save.

        """
        raise NotImplementedError


class PortiaStreamMetricsBackend(StreamMetricsBackend):
    """Backend for saving stream metrics to the Portia API."""

    def __init__(self, config: Config) -> None:
        """Init config."""
        self.config = config

    def client(self) -> httpx.Client:
        """Return an authenticated HTTP client."""
        return PortiaCloudClient().get_client(self.config)

    def check_response(self, response: httpx.Response) -> None:
        """Raise if response is not successful."""
        if not response.is_success:
            raise ValueError(f"Portia API error: {response.status_code} - {response.text}")

    def save_metrics(self, metrics: list[StreamMetric]) -> None:
        """Send metrics to the Portia API for a given eval run."""
        payload = [m.model_dump() for m in metrics]

        client = self.client()
        response = client.post("/api/v0/evals/stream-metrics/", json=payload)
        self.check_response(response)


class StreamLogMetricBackend(StreamMetricsBackend):
    """Implementation of the metrics backend that logs scores.

    This backend prints average metric scores grouped by name and tags.
    """

    def flatten_dict(
        self, d: dict[str, Any], parent_key: str = "", sep: str = "."
    ) -> dict[str, Any]:
        items = []
        for k, v in d.items():
            key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self.flatten_dict(v, key, sep=sep).items())
            else:
                items.append((key, v))
        return dict(items)

    def save_metrics(self, metrics: list[StreamMetric]) -> None:
        """Log metrics via pandas.

        Converts the metrics list into a DataFrame, expands tags into columns,
        groups by metric name and tag combinations, and prints average scores.

        Args:
            metrics (list[MetricWithTag]): The metrics to log.

        """
        # flattened = []
        # for m in metrics:
        #     row = m.model_dump()
        #     row["tags"] = self.flatten_dict(row.get("tags", {}))
        #     flattened.append(row)

        # # Convert list of metrics to DataFrame
        # dataframe = pd.DataFrame(flattened)

        # # Expand the 'tags' column into separate columns
        # tags_df = dataframe["tags"].apply(pd.Series)
        # dataframe = pd.concat([dataframe.drop(columns=["tags"]), tags_df], axis=1)

        # # Determine which columns to group by: metric name + all tag columns
        # group_keys = ["name", *tags_df.columns.tolist()]

        # # Group by name + tags, then compute mean score
        # avg_scores = dataframe.groupby(group_keys)["score"].mean().reset_index()

        # # Print
        # print("\n=== Metric Averages ===")  # noqa: T201
        # print(avg_scores.to_string(index=False))  # noqa: T201
