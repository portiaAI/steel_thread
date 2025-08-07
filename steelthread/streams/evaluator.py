"""Abstract base class for stream evaluators."""

from portia import Config

from steelthread.streams.metrics import StreamMetric
from steelthread.streams.models import PlanRunStreamItem, PlanStreamItem


class StreamEvaluator:
    """Abstract base class for implementing stream evaluation logic.

    Subclasses must define logic to evaluate either a plan or a plan run,
    typically sourced from pre-recorded executions (e.g. production runs).

    Attributes:
        config (Config): Portia configuration object.

    """

    def __init__(self, config: Config) -> None:
        """Initialize the evaluator with a Portia config.

        Args:
            config (Config): Portia configuration containing model info and credentials.

        """
        super().__init__()
        self.config = config

    def process_plan(
        self,
        stream_item: PlanStreamItem,  # noqa: ARG002
    ) -> list[StreamMetric] | StreamMetric | None:
        """Process a Plan stream item.

        Args:
            stream_item (PlanStreamItem): The Plan to evaluate.

        Returns:
            list[StreamMetric] | StreamMetric: Metric(s) resulting from evaluation.

        """
        return []

    def process_plan_run(
        self,
        stream_item: PlanRunStreamItem,  # noqa: ARG002
    ) -> list[StreamMetric] | StreamMetric | None:
        """Process a PlanRunStream item.

        Args:
            stream_item (PlanRunStreamItem): The item to evaluate

        Returns:
            list[StreamMetric] | StreamMetric | None: Metric(s) or None if not applicable.

        """
        return []
