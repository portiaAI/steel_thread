"""LLM as Judge implementation."""

from portia import Config, Output, Plan
from portia.plan_run import PlanRun

from steelthread.evals.evaluator import Evaluator, PlanRunMetadata
from steelthread.evals.metrics import EvalMetric
from steelthread.evals.models import (
    Assertion,
    EvalTestCase,
    FinalOutputAssertion,
    LatencyAssertion,
    LLMAsJudgeAssertion,
    OutcomeAssertion,
    ToolCallsAssertion,
)
from steelthread.utils.llm import LLMScorer, MetricOnly


class OutputScoreCalculator:
    """Calculate the output score using simple string matching logic."""

    @staticmethod
    def calculate(output: Output | None, assertion: FinalOutputAssertion) -> float:
        """Calculate a score comparing the output to an expected value.

        Args:
            output (Output | None): The actual output from the plan run.
            assertion (FinalOutputAssertion): The expected output assertion.

        Returns:
            float: 1.0 for match, 0.0 otherwise.

        """
        output_str = str(output.get_value()) if output else ""
        expected_str = str(assertion.value)

        match assertion.output_type:
            case "exact_match":
                return 1.0 if output_str == expected_str else 0.0
            case "partial_match":
                return 1.0 if expected_str in output_str else 0.0
            case _:
                raise ValueError(f"Unknown output_type: {assertion.output_type}")


class AssertionEvaluator:
    """Evaluate assertions defined in test cases against a PlanRun."""

    def __init__(
        self,
        config: Config,
        test_case: EvalTestCase,
        plan: Plan,
        plan_run: PlanRun,
        metadata: PlanRunMetadata,
    ) -> None:
        """Initialize the evaluator with Portia config and run data.

        Args:
            config (Config): Portia config for model access or scoring.
            test_case (EvalTestCase): The test case.
            plan (Plan): The linked plan.
            plan_run (PlanRun): The plan run to evaluate.
            metadata (PlanRunMetadata): Additional data about the run (e.g., latency, tool calls).

        """
        self.config = config
        self.test_case = test_case
        self.plan = plan
        self.plan_run = plan_run
        self.metadata = metadata

    def evaluate(self, assertion: Assertion) -> list[EvalMetric]:
        """Evaluate a single assertion and return one or more EvalMetrics.

        Args:
            assertion (Assertion): The assertion to evaluate.

        Returns:
            list[EvalMetric]: One or more EvalMetric results.

        """
        match assertion.type:
            case "outcome":
                return [self._evaluate_outcome(assertion)]
            case "final_output":
                return self._evaluate_final_output(assertion)
            case "latency":
                return [self._evaluate_latency(assertion)]
            case "tool_calls":
                return [self._evaluate_tool_calls(assertion)]
            case "llm_as_judge":
                return self._evaluate_llm_judge(assertion)
            case "custom":
                return []
            case _:
                raise ValueError(f"Unsupported assertion type: {assertion.type}")

    def _format_eval_output(self) -> dict:
        """Format the eval output for evaluation."""
        return {
            "plan_run": self.plan_run,
            "plan": self.plan,
            "metadata": self.metadata,
        }

    def _evaluate_llm_judge(self, assertion: LLMAsJudgeAssertion) -> list[EvalMetric]:
        scorer = LLMScorer(self.config)
        metrics = scorer.score(
            task_data=[
                f"Please score the given plan run based on these rules. Rules:{assertion.value}",
                self.plan_run.model_dump_json(),
            ],
            metrics_to_score=[
                MetricOnly(
                    name=assertion.type,
                    description="LLM-based score",
                )
            ],
        )
        return [
            EvalMetric.from_test_case(
                test_case=self.test_case,
                score=m.score,
                name=m.name,
                expectation=assertion.value,
                description=m.description,
                explanation=m.explanation,
                eval_output=self._format_eval_output(),
            )
            for m in metrics
        ]

    def _evaluate_outcome(self, assertion: OutcomeAssertion) -> EvalMetric:
        """Evaluate the final state of the plan run."""
        assertion_value = assertion.value.lower()
        actual_value = self.plan_run.state.lower()

        score = 1 if assertion_value == actual_value else 0
        return EvalMetric.from_test_case(
            test_case=self.test_case,
            score=score,
            name=assertion.type,
            expectation=assertion_value,
            actual_value=actual_value,
            description="Whether the outcome exactly matches expected value",
            eval_output=self._format_eval_output(),
        )

    def _evaluate_final_output(self, assertion: FinalOutputAssertion) -> list[EvalMetric]:
        """Evaluate the final output using either string comparison or LLM-based scoring."""
        assertion_value = assertion.value
        actual_value = str(
            self.plan_run.outputs.final_output.get_value()
            if self.plan_run.outputs.final_output
            else ""
        )

        if assertion.output_type == "llm_judge":
            scorer = LLMScorer(self.config)
            metrics = scorer.score(
                task_data=[
                    f"Please score based on how well the output matches {assertion.value}",
                    self.plan_run.model_dump_json(),
                ],
                metrics_to_score=[
                    MetricOnly(
                        name=assertion.type,
                        description="LLM-based final output score",
                    )
                ],
            )
            return [
                EvalMetric.from_test_case(
                    test_case=self.test_case,
                    score=m.score,
                    name=m.name,
                    expectation=assertion_value,
                    actual_value=actual_value,
                    description=m.description,
                    explanation=m.explanation,
                    eval_output=self._format_eval_output(),
                )
                for m in metrics
            ]

        score = OutputScoreCalculator.calculate(self.plan_run.outputs.final_output, assertion)
        return [
            EvalMetric.from_test_case(
                test_case=self.test_case,
                score=score,
                name=assertion.type,
                expectation=assertion_value,
                actual_value=actual_value,
                description="Exact or partial final output match",
                eval_output=self._format_eval_output(),
            )
        ]

    def _evaluate_latency(self, assertion: LatencyAssertion) -> EvalMetric:
        """Evaluate the latency against a threshold using normalized difference."""
        actual = self.metadata.latency_ms
        target = assertion.threshold_ms
        score = 1 - (abs(target - actual) / max(abs(target), abs(actual), 1e-8))
        return EvalMetric.from_test_case(
            test_case=self.test_case,
            score=score,
            name=assertion.type,
            expectation=str(target),
            actual_value=str(actual),
            description="Normalized latency score",
            eval_output=self._format_eval_output(),
        )

    def _evaluate_tool_calls(self, assertion: ToolCallsAssertion) -> EvalMetric:
        """Evaluate whether expected tools were called (or not called)."""
        expected_calls = 0
        actual_calls = 0

        for tool_call_name, expectation in assertion.calls.items():
            matched = [tc for tc in self.metadata.tool_calls if tc.tool_name == tool_call_name]
            if expectation.called:
                expected_calls += 1
                actual_calls += 1 if matched else 0
            elif matched:
                actual_calls += 1

        if expected_calls == 0 and actual_calls == 0:
            score = 1.0
        elif expected_calls > 0:
            score = min(actual_calls / expected_calls, 1.0)
        else:
            score = 0.0

        return EvalMetric.from_test_case(
            test_case=self.test_case,
            score=score,
            name=assertion.type,
            expectation=[
                tool_name for tool_name in assertion.calls if assertion.calls[tool_name].called
            ],
            actual_value=[tc.tool_name for tc in self.metadata.tool_calls],
            description="Tool call usage score",
            eval_output=self._format_eval_output(),
        )


class DefaultEvaluator(Evaluator):
    """Default implementation of an evaluator that evaluates test case assertions."""

    def eval_test_case(
        self,
        test_case: EvalTestCase,
        final_plan: Plan,
        final_plan_run: PlanRun,
        additional_data: PlanRunMetadata,
    ) -> list[EvalMetric] | None:
        """Evaluate all assertions defined in the test case.

        Args:
            test_case (TestCase): The test case to evaluate.
            final_plan (Plan): The executed plan to evaluate.
            final_plan_run (PlanRun): The executed plan run to evaluate.
            additional_data (PlanRunMetadata): Additional context like latency, tool usage.

        Returns:
            list[EvalMetric] | None: A list of EvalMetrics derived from assertions, or None if none.

        """
        evaluator = AssertionEvaluator(
            self.config, test_case, final_plan, final_plan_run, additional_data
        )
        all_metrics = []
        for assertion in test_case.assertions:
            all_metrics.extend(evaluator.evaluate(assertion))
        return all_metrics
