"""Core offline evaluator abstraction."""

from abc import ABC, abstractmethod

from portia import Config, PlanRun
from portia.storage import ToolCallRecord
from pydantic import BaseModel

from steelthread.metrics.metric import Metric
from steelthread.offline_evaluators.test_case import OfflineTestCase


class PlanRunMetadata(BaseModel):
    """Model that records metadata for a plan run.

    Attributes:
        tool_calls (list[ToolCallRecord]): A list of tool calls made during the run.
        latency_ms (float): Latency in milliseconds for the plan run.

    """

    tool_calls: list[ToolCallRecord]
    latency_ms: float


class OfflineEvaluator(ABC):
    """Abstract base class for implementing offline evaluation logic.

    Subclasses should implement the `eval_test_case` method to evaluate
    a `PlanRun` against an `OfflineTestCase` and return one or more metrics.

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
        test_case: OfflineTestCase,
        final_plan_run: PlanRun,
        additional_data: PlanRunMetadata,
    ) -> list[Metric] | Metric | None:
        """Evaluate a test case given its plan run result and metadata.

        Args:
            test_case (OfflineTestCase): The test case defining expected behavior/assertions.
            final_plan_run (PlanRun): The plan run output to evaluate.
            additional_data (PlanRunMetadata): Metadata like latency and tool call history.

        Returns:
            list[Metric] | Metric | None: One or more metrics representing evaluation results.

        """
        return []
