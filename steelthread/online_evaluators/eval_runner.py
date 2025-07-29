"""Online eval runner for steel thread."""

from concurrent.futures import ThreadPoolExecutor, as_completed

from portia import Config, Plan, PlanRun
from portia.portia import PortiaCloudStorage
from portia.prefixed_uuid import PLAN_RUN_UUID_PREFIX, PlanRunUUID, PlanUUID
from portia.storage import PLAN_UUID_PREFIX

from steelthread.common.models import EvalRun
from steelthread.metrics.metric import (
    LogMetricBackend,
    Metric,
    MetricsBackend,
    MetricTagger,
    MetricWithTag,
)
from steelthread.online_evaluators.evaluator import OnlineEvaluator
from steelthread.online_evaluators.llm_as_judge import LLMJudgeOnlineEvaluator
from steelthread.online_evaluators.test_case import OnlineTestCase
from steelthread.portia.backend import PortiaBackend


class OnlineEvalConfig:
    """Configuration for running online evaluations.

    Attributes:
        data_set_name (str): The name of the dataset containing test cases.
        portia_config (Config): Configuration for connecting to Portia API.
        iterations (int): Number of times to run each evaluation (default 3).
        evaluators (list[OnlineEvaluator]): List of evaluator instances to apply.
        additional_tags (dict[str, str]): Tags to apply to generated metrics.
        metrics_backends (list[MetricsBackend]): Output destinations for metrics.
        max_concurrency (int | None): Maximum number of concurrent tests to run.

    """

    def __init__(
        self,
        data_set_name: str,
        config: Config,
        iterations: int | None = None,
        evaluators: list[OnlineEvaluator] | None = None,
        additional_tags: dict[str, str] | None = None,
        metrics_backends: list[MetricsBackend] | None = None,
        max_concurrency: int | None = None,
    ) -> None:
        """Initialize the evaluation configuration.

        Args:
            data_set_name (str): Dataset to evaluate.
            config (Config): Portia config (must include API key).
            iterations (int | None): Number of times to run each test case.
            evaluators (list[OnlineEvaluator] | None): Evaluators to apply.
            additional_tags (dict[str, str] | None): Extra tags to add to each metric.
            metrics_backends (list[MetricsBackend] | None): Metric writers.
            max_concurrency (int | None): Maximum number of concurrent tests to run.

        """
        config.must_get_api_key("portia_api_key")
        self.data_set_name = data_set_name
        self.portia_config = config
        self.iterations = iterations or 3
        self.evaluators = evaluators or [LLMJudgeOnlineEvaluator(config)]
        self.additional_tags = additional_tags or {}
        self.metrics_backends = metrics_backends or [LogMetricBackend()]
        self.max_concurrency = max_concurrency or 5


class OnlineEvalRunner:
    """Runner for executing online evaluation test cases and collecting metrics."""

    def __init__(self, config: OnlineEvalConfig) -> None:
        """Initialize the runner.

        Args:
            config (OnlineEvalConfig): The configuration for the online evaluation run.

        """
        self.config = config
        self.backend = PortiaBackend(config=config.portia_config)
        self.storage = PortiaCloudStorage(config.portia_config)

    def run(self) -> None:
        """Execute all test cases in the configured dataset and save metrics.

        - Loads test cases from the backend.
        - Runs each test case for the specified number of iterations.
        - Applies all configured evaluators.
        - Marks cases as processed and writes metrics to backends.
        """
        eval_run = EvalRun(data_set_name=self.config.data_set_name, data_set_type="online")
        test_cases = self.backend.load_online_evals(self.config.data_set_name)
        all_metrics: list[MetricWithTag] = []

        futures = []
        with ThreadPoolExecutor(max_workers=self.config.max_concurrency) as executor:
            futures.extend(executor.submit(self._evaluate_test_case, tc) for tc in test_cases)

            for future in as_completed(futures):
                result = future.result()
                if result:
                    all_metrics.extend(result)

        if len(all_metrics) > 0:
            for backend in self.config.metrics_backends:
                backend.save_metrics(eval_run, all_metrics)

    def _evaluate_test_case(self, tc: OnlineTestCase) -> list[MetricWithTag]:
        """Evaluate a single test case across all iterations and evaluators."""
        obj = self._load_target(tc)
        if obj is None:
            return []

        metrics_out = []
        for _ in range(self.config.iterations):
            for evaluator in self.config.evaluators:
                metrics = self._evaluate(evaluator, tc, obj)
                if metrics:
                    metrics_out.extend(
                        MetricTagger.attach_tags(
                            self.config.portia_config,
                            m,
                            self.config.additional_tags,
                        )
                        for m in (metrics if isinstance(metrics, list) else [metrics])
                    )
        self.backend.mark_processed(tc)
        return metrics_out

    def _load_target(self, tc: OnlineTestCase) -> Plan | PlanRun | None:
        """Load the plan or plan run associated with a test case.

        Args:
            tc: The test case containing the reference to the related object.

        Returns:
            Plan | PlanRun | None: The retrieved object, or None if type is unsupported.

        """
        if tc.related_item_type == "plan":
            return self.storage.get_plan(
                PlanUUID.from_string(f"{PLAN_UUID_PREFIX}-{tc.related_item_id}")
            )
        if tc.related_item_type == "plan_run":
            return self.storage.get_plan_run(
                PlanRunUUID.from_string(f"{PLAN_RUN_UUID_PREFIX}-{tc.related_item_id}")
            )
        return None

    def _evaluate(
        self,
        evaluator: OnlineEvaluator,
        tc: OnlineTestCase,
        obj: Plan | PlanRun,
    ) -> list[Metric] | Metric | None:
        """Apply the evaluator to a given test case object.

        Args:
            evaluator (OnlineEvaluator): The evaluator to use.
            tc: The test case to evaluate.
            obj: The plan or plan run being evaluated.

        Returns:
            list[Metric] | Metric | None: The evaluation result.

        """
        if tc.related_item_type == "plan":
            if not isinstance(obj, Plan):
                raise ValueError("cannot eval plan when provided plan_run")
            return evaluator.eval_plan(obj)
        if tc.related_item_type == "plan_run":
            if not isinstance(obj, PlanRun):
                raise ValueError("cannot eval plan-run when provided plan")
            return evaluator.eval_plan_run(obj)
        raise ValueError("invalid related item type")
