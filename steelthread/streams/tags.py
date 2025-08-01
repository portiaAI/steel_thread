"""Class for tagging metrics."""

from portia import Config

from steelthread.streams.metrics import StreamMetric
from steelthread.streams.models import PlanRunStreamItem, PlanStreamItem


class StreamMetricTagger:
    """Class for attaching tags to metrics."""

    @staticmethod
    def attach_tags(
        metrics: list[StreamMetric] | StreamMetric,
        stream_item: PlanStreamItem | PlanRunStreamItem,
        config: Config,
        additional_tags: dict[str, str] | None = None,
    ) -> list[StreamMetric]:
        """Attach configuration-based and additional tags to a metric.

        Args:
            tc (OnlineTestCase | OfflineTestCase): the
            config (Config): Configuration object providing model names.
            metric (Metric): The original metric to tag.
            additional_tags (dict[str, str] | None): Extra tags to include (optional).

        Returns:
            MetricWithTag: The metric augmented with tags.

        """

        def append_tags(m: StreamMetric) -> StreamMetric:
            m.tags = {
                "stream": str(stream_item.stream),
                "planning_model": config.get_planning_model().model_name,
                "execution_model": config.get_execution_model().model_name,
                "introspection_model": config.get_introspection_model().model_name,
                "summarizer_model": config.get_summarizer_model().model_name,
                **(additional_tags or {}),
            }
            return m

        if isinstance(metrics, StreamMetric):
            return [append_tags(metrics)]
        return [append_tags(m) for m in metrics]
