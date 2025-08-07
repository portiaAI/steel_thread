"""Class for tagging metrics."""

from steelthread.streams.metrics import StreamMetric
from steelthread.streams.models import PlanRunStreamItem, PlanStreamItem


class StreamMetricTagger:
    """Class for attaching tags to metrics."""

    @staticmethod
    def attach_tags(
        metrics: list[StreamMetric] | StreamMetric,
        stream_item: PlanStreamItem | PlanRunStreamItem,  # noqa: ARG004
        additional_tags: dict[str, str] | None = None,
    ) -> list[StreamMetric]:
        """Attach configuration-based and additional tags to a metric.

        Args:
            metrics (list[StreamMetric] | StreamMetric): The original metrics to tag.
            stream_item (PlanStreamItem | PlanRunStreamItem): the item the metric is for.
            additional_tags (dict[str, str] | None): Extra tags to include (optional).

        Returns:
            MetricWithTag: The metric augmented with tags.

        """

        def append_tags(m: StreamMetric) -> StreamMetric:
            m.tags = {
                **(additional_tags or {}),
            }
            return m

        if isinstance(metrics, StreamMetric):
            return [append_tags(metrics)]
        return [append_tags(m) for m in metrics]
