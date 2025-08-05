"""Stream Processor for steel thread."""

from concurrent.futures import ThreadPoolExecutor, as_completed

from portia import Config
from portia.portia import PortiaCloudStorage

from steelthread.streams.backend import PortiaStreamBackend
from steelthread.streams.evaluator import StreamEvaluator
from steelthread.streams.llm_as_judge import LLMJudgeEvaluator
from steelthread.streams.metrics import (
    PortiaStreamMetricsBackend,
    StreamLogMetricBackend,
    StreamMetric,
    StreamMetricsBackend,
)
from steelthread.streams.models import PlanRunStreamItem, PlanStreamItem, Stream, StreamSource
from steelthread.streams.tags import StreamMetricTagger


class StreamConfig:
    """Configuration for processing streams.

    Attributes:
        stream_name (str): The name of the evals containing test cases.
        portia_config (Config): Configuration for connecting to Portia API.
        iterations (int): Number of times to run each evaluation (default 3).
        evaluators (list[StreamEvaluator]): List of evaluator instances to apply.
        additional_tags (dict[str, str]): Tags to apply to generated metrics.
        metrics_backends (list[MetricsBackend]): Output destinations for metrics.
        max_concurrency (int | None): Maximum number of concurrent tests to run.
        batch_size (int | None): Maximum number of items to process.

    """

    def __init__(
        self,
        stream_name: str,
        config: Config,
        evaluators: list[StreamEvaluator] | None = None,
        additional_tags: dict[str, str] | None = None,
        metrics_backends: list[StreamMetricsBackend] | None = None,
        max_concurrency: int | None = None,
        batch_size: int | None = None,
    ) -> None:
        """Initialize the evaluation configuration.

        Args:
            stream_name (str): stream name to process.
            config (Config): Portia config (must include API key).
            evaluators (list[StreamEvaluator] | None): Evaluators to apply.
            additional_tags (dict[str, str] | None): Extra tags to add to each metric.
            metrics_backends (list[MetricsBackend] | None): Metric writers.
            max_concurrency (int | None): Maximum number of concurrent tests to run.
            batch_size (int | None): Number of items to process.

        """
        config.must_get_api_key("portia_api_key")
        self.stream_name = stream_name
        self.portia_config = config
        self.evaluators = evaluators or [LLMJudgeEvaluator(config)]
        self.additional_tags = additional_tags or {}
        self.metrics_backends = metrics_backends or [
            StreamLogMetricBackend(),
            PortiaStreamMetricsBackend(config),
        ]
        self.max_concurrency = max_concurrency or 5
        self.batch_size = batch_size or 10


class StreamProcessor:
    """Runner for executing stream evaluation test cases and collecting metrics."""

    def __init__(self, config: StreamConfig) -> None:
        """Initialize the runner.

        Args:
            config (StreamConfig): The configuration for the stream.

        """
        self.config = config
        self.backend = PortiaStreamBackend(config=config.portia_config)
        self.storage = PortiaCloudStorage(config.portia_config)

    def run(self) -> None:
        """Execute all test cases in the configured dataset and save metrics.

        - Loads test cases from the backend.
        - Runs each test case for the specified number of iterations.
        - Applies all configured evaluators.
        - Marks cases as processed and writes metrics to backends.
        """
        stream = self.backend.get_stream(self.config.stream_name)

        if stream.source == StreamSource.PLAN:
            return self._process_plan(stream)
        if stream.source == StreamSource.PLAN_RUN:
            return self._process_plan_runs(stream)

        raise ValueError("invalid source")

    def _process_plan(self, stream: Stream) -> None:
        items = self.backend.load_plan_stream_items(
            stream.id,
            self.config.batch_size,
        )
        all_metrics: list[StreamMetric] = []

        futures = []
        with ThreadPoolExecutor(max_workers=self.config.max_concurrency) as executor:
            futures.extend(executor.submit(self._evaluate_plan_stream_item, item) for item in items)

            for future in as_completed(futures):
                result: list[StreamMetric] | StreamMetric | None = future.result()
                if result:
                    all_metrics.extend(result) if isinstance(result, list) else all_metrics.append(
                        result
                    )

        if len(all_metrics) > 0:
            for backend in self.config.metrics_backends:
                backend.save_metrics(all_metrics)

    def _evaluate_plan_stream_item(self, stream_item: PlanStreamItem) -> list[StreamMetric]:
        """Evaluate a single test case across all evaluators."""
        metrics_out = []
        for evaluator in self.config.evaluators:
            metrics = evaluator.process_plan(stream_item)
            if metrics:
                metrics_out.extend(
                    StreamMetricTagger.attach_tags(
                        metrics,
                        stream_item,
                        self.config.additional_tags,
                    )
                )

        self.backend.mark_processed(stream_item)
        return metrics_out

    def _process_plan_runs(self, stream: Stream) -> None:
        items = self.backend.load_plan_run_stream_items(
            stream.id,
            self.config.batch_size,
        )
        all_metrics: list[StreamMetric] = []

        futures = []
        with ThreadPoolExecutor(max_workers=self.config.max_concurrency) as executor:
            futures.extend(
                executor.submit(self._evaluate_plan_run_stream_item, item) for item in items
            )

            for future in as_completed(futures):
                result: list[StreamMetric] | StreamMetric | None = future.result()
                if result:
                    all_metrics.extend(result) if isinstance(result, list) else all_metrics.append(
                        result
                    )

        if len(all_metrics) > 0:
            for backend in self.config.metrics_backends:
                backend.save_metrics(all_metrics)

    def _evaluate_plan_run_stream_item(self, stream_item: PlanRunStreamItem) -> list[StreamMetric]:
        """Evaluate a single test case across all evaluators."""
        metrics_out: list[StreamMetric] = []
        for evaluator in self.config.evaluators:
            metrics = evaluator.process_plan_run(stream_item)
            if metrics:
                metrics_out.extend(
                    StreamMetricTagger.attach_tags(
                        metrics,
                        stream_item,
                        self.config.additional_tags,
                    )
                )

        self.backend.mark_processed(stream_item)
        return metrics_out
