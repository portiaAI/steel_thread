"""Online LLM as Judge implementation."""

from portia import Config, Plan
from portia.plan_run import PlanRun

from steelthread.common.llm import LLMMetricScorer
from steelthread.metrics.metric import Metric
from steelthread.online_evaluators.evaluator import OnlineEvaluator


class LLMJudgeOnlineEvaluator(OnlineEvaluator):
    """Online evaluator that uses an LLM to score Plans and PlanRuns.

    This evaluator uses an LLM-as-Judge approach to assign scores to logical
    properties such as correctness, completeness, and success, based on the
    JSON-serialized plan or run.
    """

    def __init__(self, config: Config) -> None:
        """Initialize the evaluator with a Portia config and LLM scorer.

        Args:
            config (Config): Portia configuration with access to default model.

        """
        self.config = config
        self.scorer = LLMMetricScorer(config)

    def eval_plan(self, plan: Plan) -> list[Metric]:
        """Evaluate a Plan (not executed) using LLM-based scoring.

        Args:
            plan (Plan): The Plan to evaluate, including its structure and logic.

        Returns:
            list[Metric]: A list of metrics scored by the LLM.

        """
        task_data = plan.model_dump_json()
        return self.scorer.score(
            task_data=[task_data],
            metrics_to_score=[
                Metric(
                    name="correctness",
                    description="Are the steps logically sound and valid?",
                    score=0,
                ),
                Metric(
                    name="completeness",
                    description="Are all necessary steps included?",
                    score=0,
                ),
                Metric(
                    name="clearness",
                    description="Are the steps clearly explained?",
                    score=0,
                ),
            ],
        )

    def eval_plan_run(self, plan_run: PlanRun) -> list[Metric]:
        """Evaluate a PlanRun (executed plan) using LLM-based scoring.

        Args:
            plan_run (PlanRun): The executed plan run to evaluate.

        Returns:
            list[Metric]: A list of performance metrics scored by the LLM.

        """
        task_data = plan_run.model_dump_json()
        return self.scorer.score(
            task_data=[task_data],
            metrics_to_score=[
                Metric(
                    name="success",
                    description="Did it accomplish the intended goal?",
                    score=0,
                ),
                Metric(
                    name="efficiency",
                    description="Were the steps necessary and minimal?",
                    score=0,
                ),
            ],
        )
