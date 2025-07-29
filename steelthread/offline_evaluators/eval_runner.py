"""Offline eval runner for steel thread."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from portia import Config, PlanRun, Portia
from portia.prefixed_uuid import PlanUUID
from portia.storage import PLAN_UUID_PREFIX

from steelthread.common.models import EvalRun
from steelthread.metrics.metric import (
    LogMetricBackend,
    Metric,
    MetricsBackend,
    MetricTagger,
)
from steelthread.offline_evaluators.default_evaluator import DefaultOfflineEvaluator
from steelthread.offline_evaluators.evaluator import OfflineEvaluator, PlanRunMetadata
from steelthread.offline_evaluators.test_case import OfflineTestCase
from steelthread.portia.backend import PortiaBackend
from steelthread.portia.storage import ReadOnlyStorage
from steelthread.portia.tools import ToolStubRegistry


class OfflineEvalConfig:
    """Configuration for running offline evaluations.

    Attributes:
        data_set_name (str): The name of the test dataset to evaluate.
        portia_config (Config): Portia configuration object.
        iterations (int): Number of times each test case should be run (defaults to 3).
        evaluators (list[OfflineEvaluator]): List of evaluators to apply to each run.
        additional_tags (dict[str, str]): Tags to attach to each metric result.
        metrics_backends (list[MetricsBackend]): Where to send/save metric results.
        max_concurrency (int | None): Maximum number of concurrent tests to run.

    """

    def __init__(
        self,
        data_set_name: str,
        config: Config,
        iterations: int | None = None,
        evaluators: list[OfflineEvaluator] | None = None,
        additional_tags: dict[str, str] | None = None,
        metrics_backends: list[MetricsBackend] | None = None,
        max_concurrency: int | None = None,
    ) -> None:
        """Initialize OfflineEvalConfig.

        Args:
            data_set_name (str): Name of the dataset to evaluate.
            config (Config): Portia config with API key.
            iterations (int | None): How many times to run each test case.
            evaluators (list[OfflineEvaluator] | None): Evaluators to use (defaults to built-in).
            additional_tags (dict[str, str] | None): Custom tags to attach to metrics.
            metrics_backends (list[MetricsBackend] | None): Output backends (defaults to logger).
            max_concurrency (int | None): Maximum number of concurrent tests to run.

        """
        config.must_get_api_key("portia_api_key")
        self.data_set_name = data_set_name
        self.portia_config = config
        self.iterations = iterations or 3
        self.evaluators = evaluators or [DefaultOfflineEvaluator(config)]
        self.additional_tags = additional_tags or {}
        self.metrics_backends = metrics_backends or [LogMetricBackend()]
        self.max_concurrency = max_concurrency or 5


class OfflineEvalRunner:
    """Runner for executing and scoring offline evaluations."""

    def __init__(self, portia: Portia, config: OfflineEvalConfig) -> None:
        """Initialize the runner.

        Wraps the tool registry for stubbing and enforces read-only plan storage.

        Args:
            portia (Portia): Portia engine instance to execute runs.
            config (OfflineEvalConfig): Offline evaluation configuration.

        """
        self.portia = portia
        self.config = config
        self.backend = PortiaBackend(config=config.portia_config)

        self.tool_registry = (
            ToolStubRegistry(portia.tool_registry, stubs={})
            if not isinstance(portia.tool_registry, ToolStubRegistry)
            else portia.tool_registry
        )
        portia.tool_registry = self.tool_registry
        portia.storage = ReadOnlyStorage(portia.storage)  # type: ignore  # noqa: PGH003

    def _evaluate_and_collect_metrics(self, tc: OfflineTestCase) -> list[Metric]:
        """Run a single test case with isolated tool registry and evaluators."""
        inner_registry = self.portia.tool_registry
        tool_registry = ToolStubRegistry(inner_registry, stubs={})

        # Patch a local Portia with the test-specific tool registry
        portia = Portia(config=self.config.portia_config, tools=tool_registry)
        portia.storage = ReadOnlyStorage(portia.storage)  # type: ignore  # noqa: PGH003

        # Run the test case
        output, latency = self._run_test_case(tc)

        # Evaluate with isolated evaluator instances
        all_metrics = []
        for evaluator in self.config.evaluators:
            metrics = evaluator.eval_test_case(
                tc,
                output,
                PlanRunMetadata(
                    latency_ms=latency,
                    tool_calls=tool_registry.get_tool_calls(),
                ),
            )
            if metrics:
                all_metrics.extend(
                    [
                        MetricTagger.attach_tags(
                            self.config.portia_config, m, self.config.additional_tags
                        )
                        for m in (metrics if isinstance(metrics, list) else [metrics])
                    ]
                )
        return all_metrics

    def run(self) -> None:
        """Run the offline evaluation process.

        - Loads test cases from backend.
        - Executes each test case multiple times.
        - Applies evaluators to generate metrics.
        - Saves metrics using configured backends.

        """
        eval_run = EvalRun(data_set_name=self.config.data_set_name, data_set_type="offline")
        test_cases = self.backend.load_offline_evals(self.config.data_set_name)
        all_metrics = []

        futures = []

        with ThreadPoolExecutor(max_workers=self.config.max_concurrency) as executor:
            futures.extend(
                executor.submit(self._evaluate_and_collect_metrics, tc)
                for tc in test_cases
                for _ in range(self.config.iterations)
            )

            for future in as_completed(futures):
                metrics = future.result()
                if metrics:
                    all_metrics.extend(metrics)

        if len(all_metrics) > 0:
            for backend in self.config.metrics_backends:
                backend.save_metrics(eval_run, all_metrics)

    def _run_test_case(self, tc: OfflineTestCase) -> tuple[PlanRun, float]:
        """Execute a single test case and record latency.

        Args:
            tc: The offline test case to run.

        Returns:
            tuple: The plan run output and latency in milliseconds.

        """
        start = time.perf_counter()
        if tc.input_config.type == "query":
            output = self.portia.run(tc.input_config.value, tools=tc.input_config.tools)
        elif tc.input_config.type == "plan_id":
            output = self.portia.run_plan(
                PlanUUID.from_string(f"{PLAN_UUID_PREFIX}-{tc.input_config.value}")
            )
        else:
            raise ValueError(f"invalid input_config type: {tc.input_config.type}")
        end = time.perf_counter()
        return output, (end - start) * 1000
