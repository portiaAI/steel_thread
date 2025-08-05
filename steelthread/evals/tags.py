"""Class for tagging metrics."""

from portia import Config, Plan, PlanRun

from steelthread.evals.metrics import EvalMetric
from steelthread.evals.models import EvalTestCase


class EvalMetricTagger:
    """Class for attaching tags to metrics."""

    @staticmethod
    def attach_tags_to_test_case(
        metrics: list[EvalMetric] | EvalMetric,
        test_case: EvalTestCase,
        plan: Plan,  # noqa: ARG004
        plan_run: PlanRun | None,  # noqa: ARG004
        config: Config,
        additional_tags: dict[str, str] | None = None,
    ) -> list[EvalMetric]:
        """Attach configuration-based and additional tags to a metric.

        Args:
            metrics (list[EvalMetric] | EvalMetric): the original metrics to tag.
            test_case (EvalTestCase): the original test case.
            plan (Plan): The associated plan
            plan_run (PlanRun): The associated plan_run
            config (Config): Portia config used.
            additional_tags (dict[str, str] | None): Extra tags to include (optional).

        Returns:
            MetricWithTag: The metric augmented with tags.

        """

        def append_tags(m: EvalMetric) -> EvalMetric:
            m.tags = {
                "test_case": str(test_case.testcase),
                "planning_model": config.get_planning_model().model_name,
                "execution_model": config.get_execution_model().model_name,
                "introspection_model": config.get_introspection_model().model_name,
                "summarizer_model": config.get_summarizer_model().model_name,
                **(additional_tags or {}),
            }
            return m

        if isinstance(metrics, EvalMetric):
            return [append_tags(metrics)]
        return [append_tags(m) for m in metrics]
