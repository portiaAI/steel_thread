"""LLM as Judge implementation."""

from portia import Config

from steelthread.streams.evaluator import StreamEvaluator
from steelthread.streams.metrics import StreamMetric
from steelthread.streams.models import PlanRunStreamItem, PlanStreamItem
from steelthread.utils.llm import LLMScorer, MetricOnly


class LLMJudgeEvaluator(StreamEvaluator):
    """Evaluator that uses an LLM to score Plans and PlanRuns.

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
        self.scorer = LLMScorer(config)

    def process_plan(self, stream_item: PlanStreamItem) -> list[StreamMetric]:
        """Evaluate a Plan (not executed) using LLM-based scoring.

        Args:
            stream_item (PlanStreamItem): The Plan to evaluate.

        Returns:
            list[Metric]: A list of metrics scored by the LLM.

        """
        task_data = stream_item.plan.model_dump_json()
        metrics = self.scorer.score(
            task_data=[task_data],
            metrics_to_score=[
                MetricOnly(
                    name="correctness",
                    description="Are the steps logically sound and valid?",
                ),
                MetricOnly(
                    name="completeness",
                    description="Are all necessary steps included?",
                ),
                MetricOnly(
                    name="clearness",
                    description="Are the steps clearly explained?",
                ),
            ],
        )

        return [
            StreamMetric.from_stream_item(
                stream_item=stream_item,
                score=m.score,
                name=m.name,
                description=m.description,
                explanation=m.explanation,
            )
            for m in metrics
        ]

    def process_plan_run(self, stream_item: PlanRunStreamItem) -> list[StreamMetric]:
        """Evaluate a PlanRun (executed plan) using LLM-based scoring.

        Args:
            stream_item (PlanRunStreamItem): The linked plan + plan_run to process.

        Returns:
            list[Metric]: A list of performance metrics scored by the LLM.

        """
        task_data = f"""
         plan: {stream_item.plan.model_dump_json()}
         plan_run: {stream_item.plan_run.model_dump_json()}
        """
        metrics = self.scorer.score(
            task_data=[task_data],
            metrics_to_score=[
                MetricOnly(
                    name="success",
                    description="Did it accomplish the intended goal?",
                ),
                MetricOnly(
                    name="efficiency",
                    description="Were the steps necessary and minimal?",
                ),
            ],
        )

        return [
            StreamMetric.from_stream_item(
                stream_item=stream_item,
                score=m.score,
                name=m.name,
                description=m.description,
                explanation=m.explanation,
            )
            for m in metrics
        ]
