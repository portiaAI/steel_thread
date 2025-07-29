"""Abstract base class for online evaluators."""

from abc import ABC, abstractmethod

from portia import Config, Plan, PlanRun

from steelthread.metrics.metric import Metric


class OnlineEvaluator(ABC):
    """Abstract base class for implementing online evaluation logic.

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

    @abstractmethod
    def eval_plan(self, plan: Plan) -> list[Metric] | Metric:
        """Evaluate a static Plan definition.

        Args:
            plan (Plan): The Plan to evaluate (no runtime data).

        Returns:
            list[Metric] | Metric: Metric(s) resulting from evaluation.

        """
        return []

    @abstractmethod
    def eval_plan_run(self, plan_run: PlanRun) -> list[Metric] | Metric | None:
        """Evaluate a completed PlanRun (runtime output available).

        Args:
            plan_run (PlanRun): The executed PlanRun object to evaluate.

        Returns:
            list[Metric] | Metric | None: Metric(s) or None if not applicable.

        """
        return []
