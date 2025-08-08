"""Eval runner for steel thread."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import uuid4

from portia import Config, Plan, PlanRun, Portia
from portia.prefixed_uuid import PlanUUID

from steelthread.evals.backend import PortiaBackend
from steelthread.evals.default_evaluator import DefaultEvaluator
from steelthread.evals.evaluator import Evaluator, PlanRunMetadata
from steelthread.evals.metrics import (
    EvalLogMetricBackend,
    EvalMetric,
    MetricsBackend,
    PortiaEvalMetricsBackend,
)
from steelthread.evals.models import EvalTestCase
from steelthread.evals.tags import EvalMetricTagger
from steelthread.portia.portia import NoAuthPullPortia
from steelthread.portia.storage import ReadOnlyStorage
from steelthread.portia.tools import ToolStubRegistry


class EvalConfig:
    """Configuration for running  evaluations.

    Attributes:
        eval_dataset_name (str): The name of the test eval set to evaluate.
        portia_config (Config): Portia configuration object.
        iterations (int): Number of times each test case should be run (defaults to 3).
        evaluators (list[Evaluator]): List of evaluators to apply to each run.
        additional_tags (dict[str, str]): Tags to attach to each metric result.
        metrics_backends (list[MetricsBackend]): Where to send/save metric results.
        max_concurrency (int | None): Maximum number of concurrent tests to run.

    """

    def __init__(
        self,
        eval_dataset_name: str,
        config: Config,
        iterations: int | None = None,
        evaluators: list[Evaluator] | None = None,
        additional_tags: dict[str, str] | None = None,
        metrics_backends: list[MetricsBackend] | None = None,
        max_concurrency: int | None = None,
    ) -> None:
        """Initialize EvalConfig.

        Args:
            eval_dataset_name (str): Name of the eval set to evaluate.
            config (Config): Portia config with API key.
            iterations (int | None): How many times to run each test case.
            evaluators (list[Evaluator] | None): Evaluators to use (defaults to built-in).
            additional_tags (dict[str, str] | None): Custom tags to attach to metrics.
            metrics_backends (list[MetricsBackend] | None): Output backends (defaults to logger).
            max_concurrency (int | None): Maximum number of concurrent tests to run.

        """
        config.must_get_api_key("portia_api_key")
        self.eval_dataset_name = eval_dataset_name
        self.portia_config = config
        self.iterations = iterations or 3
        self.evaluators = evaluators or [DefaultEvaluator(config)]
        self.additional_tags = additional_tags or {}
        self.metrics_backends = metrics_backends or [
            EvalLogMetricBackend(),
            PortiaEvalMetricsBackend(config),
        ]
        self.max_concurrency = max_concurrency or 5


class EvalRunner:
    """Runner for executing and scoring evaluations."""

    def __init__(self, portia: Portia, config: EvalConfig) -> None:
        """Initialize the runner.

        Wraps the tool registry for stubbing and enforces read-only plan storage.

        Args:
            portia (Portia): Portia engine instance to execute runs.
            config (EvalConfig): Evaluation configuration.

        """
        self.original_portia = portia
        self.config = config
        self.backend = PortiaBackend(config=config.portia_config)

    def _evaluate_and_collect_metrics(self, tc: EvalTestCase) -> list[EvalMetric]:
        """Run a single test case with isolated tool registry and evaluators."""
        inner_registry = self.original_portia.tool_registry
        tool_registry = ToolStubRegistry(inner_registry, stubs={})

        # Patch a local Portia with the test-specific tool registry
        portia = NoAuthPullPortia(config=self.config.portia_config, tools=tool_registry)
        portia.storage = ReadOnlyStorage(portia.storage)  # type: ignore  # noqa: PGH003

        # Run the test case
        plan, plan_run, latency = self._run_test_case(tc, portia)

        # Evaluate with isolated evaluator instances
        all_metrics = []
        for evaluator in self.config.evaluators:
            metrics = evaluator.eval_test_case(
                tc,
                plan,
                plan_run,
                PlanRunMetadata(
                    latency_ms=latency,
                    tool_calls=tool_registry.get_tool_calls(),
                ),
            )
            if metrics:
                all_metrics.extend(
                    EvalMetricTagger.attach_tags_to_test_case(
                        metrics,
                        tc,
                        plan,
                        plan_run,
                        self.config.portia_config,
                        self.config.additional_tags,
                    )
                )
        return all_metrics

    def run(self) -> None:
        """Run the evaluation process.

        - Loads test cases from backend.
        - Executes each test case multiple times.
        - Applies evaluators to generate metrics.
        - Saves metrics using configured backends.

        """
        run_id = str(uuid4())
        test_cases = self.backend.load_evals(self.config.eval_dataset_name, run_id)
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
                backend.save_eval_metrics(all_metrics)

    def _run_test_case(self, tc: EvalTestCase, portia: Portia) -> tuple[Plan, PlanRun, float]:
        """Execute a single test case and record latency.

        Args:
            tc: The test case to run.
            portia: The instance of portia to use.

        Returns:
            tuple: The plan run output and latency in milliseconds.

        """
        print(f"Executing test case: {tc.input_config.type} - {tc.input_config.value}")  # noqa: T201
        start = time.perf_counter()
        if tc.input_config.type == "query":
            plan = portia.plan(
                tc.input_config.value,
                tools=tc.input_config.tools,
                end_user=tc.input_config.end_user_id,
            )
            output = portia.run_plan(plan)
        elif tc.input_config.type == "plan_id":
            plan = portia.storage.get_plan(PlanUUID.from_string(tc.input_config.value))
            output = portia.run_plan(plan)
        else:
            raise ValueError(f"invalid input_config type: {tc.input_config.type}")
        end = time.perf_counter()
        return plan, output, (end - start) * 1000
