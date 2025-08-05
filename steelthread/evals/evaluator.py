"""Core evaluator abstraction."""

from abc import ABC, abstractmethod

from portia import Config, Plan, PlanRun
from portia.storage import ToolCallRecord
from pydantic import BaseModel

from steelthread.evals.metrics import EvalMetric
from steelthread.evals.models import EvalTestCase


class PlanRunMetadata(BaseModel):
    """Model that records metadata for a plan run.

    Attributes:
        tool_calls (list[ToolCallRecord]): A list of tool calls made during the run.
        latency_ms (float): Latency in milliseconds for the plan run.

    """

    tool_calls: list[ToolCallRecord]
    latency_ms: float


class Evaluator(ABC):
    """Abstract base class for implementing evaluation logic.

    Subclasses should implement the `eval_test_case` method to evaluate
    a `PlanRun` against an `EvalTestCase` and return one or more EvalMetrics.

    Attributes:
        config (Config): Portia configuration instance for access to model or tooling info.

    """

    def __init__(self, config: Config) -> None:
        """Initialize the evaluator with a Portia config.

        Args:
            config (Config): Configuration object for Portia and LLM integration.

        """
        super().__init__()
        self.config = config

    @abstractmethod
    def eval_test_case(
        self,
        test_case: EvalTestCase,
        final_plan: Plan,
        final_plan_run: PlanRun,
        additional_data: PlanRunMetadata,
    ) -> list[EvalMetric] | EvalMetric | None:
        """Evaluate a test case given its plan run result and metadata.

        Args:
            test_case (EvalTestCase): The test case defining expected behavior/assertions.
            final_plan (Plan): The plan to evaluate.
            final_plan_run (PlanRun): The plan run output to evaluate.
            additional_data (PlanRunMetadata): Metadata like latency and tool call history.

        Returns:
            list[EvalMetric] | EvalMetric | None: One or more EvalMetrics representing results.

        """
        return []
