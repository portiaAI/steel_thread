"""Test default evaluator."""

from typing import Literal
from unittest.mock import MagicMock, patch

import pytest
from portia import Plan, PlanRun, PlanRunState
from portia.tool_call import ToolCallRecord as ToolCall
from portia.tool_call import ToolCallStatus

from steelthread.common.llm import LLMMetricScorer
from steelthread.metrics.metric import Metric
from steelthread.offline_evaluators.default_evaluator import (
    AssertionEvaluator,
    DefaultOfflineEvaluator,
    OutputScoreCalculator,
)
from steelthread.offline_evaluators.evaluator import OfflineEvaluator, PlanRunMetadata
from steelthread.offline_evaluators.test_case import (
    CustomAssertion,
    FinalOutputAssertion,
    InputConfig,
    LatencyAssertion,
    OfflineTestCase,
    OutcomeAssertion,
    ToolCallRecord,
    ToolCallsAssertion,
)
from tests.unit.utils import get_test_config, get_test_plan_run


@pytest.mark.parametrize(
    ("output_value", "expected_value", "output_type", "expected_score"),
    [
        ("hello", "hello", "exact_match", 1.0),
        ("hello", "world", "exact_match", 0.0),
        ("hello world", "world", "partial_match", 1.0),
        ("hello", "moon", "partial_match", 0.0),
    ],
)
def test_output_score_calculator(
    output_value: str,
    expected_value: str,
    output_type: Literal["exact_match", "partial_match", "llm_judge"],
    expected_score: float,
) -> None:
    """Test output eval."""
    output = MagicMock()
    output.get_value.return_value = output_value
    assertion = FinalOutputAssertion(
        type="final_output", output_type=output_type, value=expected_value
    )
    score = OutputScoreCalculator.calculate(output, assertion)
    assert score == expected_score


def test_output_score_calculator_invalid() -> None:
    """Test output eval."""
    output = MagicMock()
    output.get_value.return_value = "foo"
    assertion = FinalOutputAssertion.model_construct(
        type="final_output",
        output_type="nonsense",
        value="foo",
    )
    with pytest.raises(ValueError):  # noqa: PT011
        OutputScoreCalculator.calculate(output, assertion)  # type: ignore  # noqa: PGH003


def test_unknown_assertion_match() -> None:
    """Check unknown assertion."""
    plan, plan_run = get_test_plan_run()
    plan_run.state = PlanRunState.COMPLETE
    evaluator = AssertionEvaluator(
        config=get_test_config(),
        plan=plan,
        plan_run=plan_run,
        metadata=PlanRunMetadata(tool_calls=[], latency_ms=10),
    )

    assertion = OutcomeAssertion.model_construct(type="random_type", value="COMPLETE")
    with pytest.raises(ValueError):  # noqa: PT011
        evaluator.evaluate(assertion)


def test_custom_assertion_match() -> None:
    """Check custom assertion."""
    plan, plan_run = get_test_plan_run()
    plan_run.state = PlanRunState.COMPLETE
    evaluator = AssertionEvaluator(
        config=get_test_config(),
        plan=plan,
        plan_run=plan_run,
        metadata=PlanRunMetadata(tool_calls=[], latency_ms=10),
    )

    assertion = CustomAssertion(type="custom", value={})
    assert len(evaluator.evaluate(assertion)) == 0


def test_outcome_assertion_match() -> None:
    """Check outcome match."""
    plan, plan_run = get_test_plan_run()
    plan_run.state = PlanRunState.COMPLETE
    evaluator = AssertionEvaluator(
        config=get_test_config(),
        plan=plan,
        plan_run=plan_run,
        metadata=PlanRunMetadata(tool_calls=[], latency_ms=10),
    )
    [metric] = evaluator.evaluate(OutcomeAssertion(type="outcome", value="COMPLETE"))
    assert metric.score == 1


def test_outcome_assertion_mismatch() -> None:
    """Check outcome mismatch."""
    plan, plan_run = get_test_plan_run()
    plan_run.state = PlanRunState.COMPLETE
    evaluator = AssertionEvaluator(
        config=get_test_config(),
        plan=plan,
        plan_run=plan_run,
        metadata=PlanRunMetadata(tool_calls=[], latency_ms=10),
    )
    [metric] = evaluator.evaluate(OutcomeAssertion(type="outcome", value="FAILED"))
    assert metric.score == 0


def test_latency_assertion() -> None:
    """Check Latency assertion."""
    plan, plan_run = get_test_plan_run()
    evaluator = AssertionEvaluator(
        config=get_test_config(),
        plan=plan,
        plan_run=plan_run,
        metadata=PlanRunMetadata(tool_calls=[], latency_ms=9000),
    )
    [metric] = evaluator.evaluate(LatencyAssertion(type="latency", threshold_ms=10000))
    assert metric.name == "latency"
    assert metric.score == 0.9

    evaluator = AssertionEvaluator(
        config=get_test_config(),
        plan=plan,
        plan_run=plan_run,
        metadata=PlanRunMetadata(tool_calls=[], latency_ms=12000),
    )
    [metric] = evaluator.evaluate(LatencyAssertion(type="latency", threshold_ms=10000))
    assert metric.name == "latency"
    assert metric.score == 0.8333333333333334


def test_tool_calls_assertion() -> None:
    """Test tool call match."""
    plan, plan_run = get_test_plan_run()
    evaluator = AssertionEvaluator(
        config=get_test_config(),
        plan=plan,
        plan_run=plan_run,
        metadata=PlanRunMetadata(
            tool_calls=[
                ToolCall(
                    tool_name="weather",
                    plan_run_id=plan_run.id,
                    step=plan_run.current_step_index,
                    end_user_id="",
                    status=ToolCallStatus.SUCCESS,
                    input={},
                    output={},
                    latency_seconds=1,
                )
            ],
            latency_ms=9000,
        ),
    )

    [metric] = evaluator.evaluate(
        ToolCallsAssertion(
            type="tool_calls",
            calls={"weather": ToolCallRecord(called=True)},
        )
    )
    assert metric.score == 1.0
    assert metric.name == "tool_calls"


def test_tool_calls_assertion_unexpected() -> None:
    """Test tool call unexpected."""
    plan, plan_run = get_test_plan_run()
    evaluator = AssertionEvaluator(
        config=get_test_config(),
        plan=plan,
        plan_run=plan_run,
        metadata=PlanRunMetadata(
            tool_calls=[
                ToolCall(
                    tool_name="weather",
                    plan_run_id=plan_run.id,
                    step=plan_run.current_step_index,
                    end_user_id="",
                    status=ToolCallStatus.SUCCESS,
                    input={},
                    output={},
                    latency_seconds=1,
                )
            ],
            latency_ms=9000,
        ),
    )

    [metric] = evaluator.evaluate(
        ToolCallsAssertion(
            type="tool_calls",
            calls={"weather": ToolCallRecord(called=False)},
        )
    )
    assert metric.score == 0
    assert metric.name == "tool_calls"


def test_tool_calls_assertion_mismatch() -> None:
    """Test tool call mismatch."""
    plan, plan_run = get_test_plan_run()
    evaluator = AssertionEvaluator(
        config=get_test_config(),
        plan=plan,
        plan_run=plan_run,
        metadata=PlanRunMetadata(tool_calls=[], latency_ms=9000),
    )

    [metric] = evaluator.evaluate(
        ToolCallsAssertion(
            type="tool_calls",
            calls={"weather": ToolCallRecord(called=True)},
        )
    )
    assert metric.score == 0
    assert metric.name == "tool_calls"


def test_final_output_assertion_llm_judge() -> None:
    """Check final output LLM judge."""
    scorer_mock = MagicMock()
    scorer_mock.score.return_value = [Metric(score=0.5, name="final_output", description="desc")]

    plan, _ = get_test_plan_run()

    plan_run = MagicMock()
    plan_run.model_dump_json.return_value = "{}"

    with patch.object(LLMMetricScorer, "score", scorer_mock.score):
        evaluator = AssertionEvaluator(
            config=get_test_config(),
            plan=plan,
            plan_run=plan_run,
            metadata=PlanRunMetadata(latency_ms=10000, tool_calls=[]),
        )

        assertion = FinalOutputAssertion(
            type="final_output", output_type="llm_judge", value="expected"
        )
        metrics = evaluator.evaluate(assertion)

    assert len(metrics) == 1
    assert metrics[0].score == 0.5


def test_default_offline_evaluator_integration() -> None:
    """Test e2e flow."""
    final_output = MagicMock()
    final_output.get_value.return_value = "foo"

    plan, plan_run = get_test_plan_run()
    metadata = PlanRunMetadata(latency_ms=10000, tool_calls=[])

    test_case = OfflineTestCase(
        id="",
        input_config=InputConfig(type="query", value=""),
        assertions=[
            OutcomeAssertion(type="outcome", value="success"),
            FinalOutputAssertion(type="final_output", output_type="exact_match", value="foo"),
            LatencyAssertion(type="latency", threshold_ms=100),
            ToolCallsAssertion(type="tool_calls", calls={}),
        ],
    )

    evaluator = DefaultOfflineEvaluator(config=get_test_config())
    metrics = evaluator.eval_test_case(test_case, plan, plan_run, metadata)

    assert isinstance(metrics, list)
    assert all(isinstance(m, Metric) for m in metrics)
    assert len(metrics) == 4


def test_eval_base_class() -> None:
    """Test base class."""

    class MyEvaluator(OfflineEvaluator):
        def eval_test_case(
            self,
            test_case: OfflineTestCase,
            final_plan: Plan,
            final_plan_run: PlanRun,
            additional_data: PlanRunMetadata,
        ) -> list[Metric] | Metric | None:
            return super().eval_test_case(test_case, final_plan, final_plan_run, additional_data)

    evaluator = MyEvaluator(get_test_config())
    plan, plan_run = get_test_plan_run()

    metadata = PlanRunMetadata(latency_ms=10000, tool_calls=[])

    test_case = OfflineTestCase(
        id="",
        input_config=InputConfig(type="query", value=""),
        assertions=[
            OutcomeAssertion(type="outcome", value="success"),
            FinalOutputAssertion(type="final_output", output_type="exact_match", value="foo"),
            LatencyAssertion(type="latency", threshold_ms=100),
            ToolCallsAssertion(type="tool_calls", calls={}),
        ],
    )

    metrics = evaluator.eval_test_case(test_case, plan, plan_run, metadata)
    assert isinstance(metrics, list)
    assert len(metrics) == 0
