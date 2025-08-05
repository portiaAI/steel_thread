"""Test default evaluator."""

from unittest.mock import patch

import pytest
from portia import Config, LocalDataValue, PlanRunState
from portia.tool_call import ToolCallRecord, ToolCallStatus

from steelthread.evals.default_evaluator import DefaultEvaluator
from steelthread.evals.evaluator import PlanRunMetadata
from steelthread.evals.models import (
    EvalTestCase,
    FinalOutputAssertion,
    InputConfig,
    LatencyAssertion,
    OutcomeAssertion,
    ToolCallAssertion,
    ToolCallsAssertion,
)
from steelthread.utils.llm import LLMMetricScorer, MetricOnly
from tests.unit.utils import get_test_config, get_test_plan_run


@pytest.fixture
def config() -> Config:
    """Config."""
    return get_test_config()


@pytest.fixture
def test_case() -> EvalTestCase:
    """Test case."""
    return EvalTestCase(
        dataset="my-dataset",
        testcase="test-1",
        run="run-1",
        input_config=InputConfig(type="query", value="query"),
        assertions=[],
    )


def test_outcome_assertion(config: Config, test_case: EvalTestCase) -> None:
    """Test outcomes."""
    plan, plan_run = get_test_plan_run()
    plan_run.state = PlanRunState.COMPLETE
    metadata = PlanRunMetadata(tool_calls=[], latency_ms=10)
    test_case.assertions = [OutcomeAssertion(type="outcome", value="COMPLETE")]
    evaluator = DefaultEvaluator(config)
    metrics = evaluator.eval_test_case(test_case, plan, plan_run, metadata)

    assert metrics
    assert len(metrics) == 1
    m = metrics[0]
    assert m.name == "outcome"
    assert m.score == 1
    assert m.expectation == "complete"
    assert m.actual_value == "complete"


def test_final_output_exact_match(config: Config, test_case: EvalTestCase) -> None:
    """Test outcomes."""
    plan, plan_run = get_test_plan_run()
    metadata = PlanRunMetadata(tool_calls=[], latency_ms=10)
    plan_run.outputs.final_output = LocalDataValue(value="This is the final output")
    test_case.assertions = [
        FinalOutputAssertion(
            type="final_output", output_type="exact_match", value="This is the final output"
        )
    ]
    evaluator = DefaultEvaluator(config)
    metrics = evaluator.eval_test_case(test_case, plan, plan_run, metadata)
    assert metrics
    assert len(metrics) == 1
    m = metrics[0]
    assert m.name == "final_output"
    assert m.score == 1.0


def test_final_output_partial_match(config: Config, test_case: EvalTestCase) -> None:
    """Test outcomes."""
    plan, plan_run = get_test_plan_run()
    metadata = PlanRunMetadata(tool_calls=[], latency_ms=10)
    plan_run.outputs.final_output = LocalDataValue(value="This is the final output")
    test_case.assertions = [
        FinalOutputAssertion(type="final_output", output_type="partial_match", value="final output")
    ]
    evaluator = DefaultEvaluator(config)
    metrics = evaluator.eval_test_case(test_case, plan, plan_run, metadata)
    assert metrics
    assert len(metrics) == 1
    assert metrics[0].score == 1.0


def test_final_output_unknown_match(config: Config, test_case: EvalTestCase) -> None:
    """Test outcomes."""
    plan, plan_run = get_test_plan_run()
    metadata = PlanRunMetadata(tool_calls=[], latency_ms=10)
    plan_run.outputs.final_output = LocalDataValue(value="This is the final output")
    test_case.assertions = [
        FinalOutputAssertion.model_construct(
            type="final_output", output_type="other", value="final output"
        )
    ]
    evaluator = DefaultEvaluator(config)
    with pytest.raises(ValueError):  # noqa: PT011
        evaluator.eval_test_case(test_case, plan, plan_run, metadata)


def test_final_output_custom(config: Config, test_case: EvalTestCase) -> None:
    """Test outcomes."""
    plan, plan_run = get_test_plan_run()
    metadata = PlanRunMetadata(tool_calls=[], latency_ms=10)
    plan_run.outputs.final_output = LocalDataValue(value="This is the final output")
    test_case.assertions = [
        FinalOutputAssertion.model_construct(
            type="custom", output_type="other", value="final output"
        )
    ]
    evaluator = DefaultEvaluator(config)

    metrics = evaluator.eval_test_case(test_case, plan, plan_run, metadata)
    assert metrics == []


def test_final_output_unknown_type(config: Config, test_case: EvalTestCase) -> None:
    """Test outcomes."""
    plan, plan_run = get_test_plan_run()
    metadata = PlanRunMetadata(tool_calls=[], latency_ms=10)
    plan_run.outputs.final_output = LocalDataValue(value="This is the final output")
    test_case.assertions = [
        FinalOutputAssertion.model_construct(
            type="fisejig", output_type="other", value="final output"
        )
    ]
    evaluator = DefaultEvaluator(config)
    with pytest.raises(ValueError):  # noqa: PT011
        evaluator.eval_test_case(test_case, plan, plan_run, metadata)


def test_latency_assertion(config: Config, test_case: EvalTestCase) -> None:
    """Test outcomes."""
    plan, plan_run = get_test_plan_run()
    metadata = PlanRunMetadata(tool_calls=[], latency_ms=10)

    test_case.assertions = [LatencyAssertion(type="latency", threshold_ms=100.0)]
    evaluator = DefaultEvaluator(config)
    metrics = evaluator.eval_test_case(test_case, plan, plan_run, metadata)

    assert metrics
    assert len(metrics) == 1
    m = metrics[0]
    assert m.name == "latency"
    assert isinstance(m.score, float)
    assert m.expectation == "100.0"
    assert m.actual_value == "10.0"


def test_tool_calls_assertion(config: Config, test_case: EvalTestCase) -> None:
    """Test outcomes."""
    plan, plan_run = get_test_plan_run()
    metadata = PlanRunMetadata(
        tool_calls=[
            ToolCallRecord(
                tool_name="my_tool",
                plan_run_id=plan_run.id,
                step=plan_run.current_step_index,
                end_user_id=plan_run.end_user_id,
                status=ToolCallStatus.SUCCESS,
                input={},
                output={},
                latency_seconds=1,
            )
        ],
        latency_ms=10,
    )

    test_case.assertions = [
        ToolCallsAssertion(type="tool_calls", calls={"my_tool": ToolCallAssertion(called=True)})
    ]
    evaluator = DefaultEvaluator(config)
    metrics = evaluator.eval_test_case(test_case, plan, plan_run, metadata)
    assert metrics
    assert len(metrics) == 1
    m = metrics[0]
    assert m.name == "tool_calls"
    assert m.expectation == ["my_tool"]
    assert isinstance(m.actual_value, list)
    assert "my_tool" in m.actual_value


def test_tool_calls_not_called_assertion(config: Config, test_case: EvalTestCase) -> None:
    """Test outcomes."""
    plan, plan_run = get_test_plan_run()
    metadata = PlanRunMetadata(
        tool_calls=[
            ToolCallRecord(
                tool_name="my_tool",
                plan_run_id=plan_run.id,
                step=plan_run.current_step_index,
                end_user_id=plan_run.end_user_id,
                status=ToolCallStatus.SUCCESS,
                input={},
                output={},
                latency_seconds=1,
            )
        ],
        latency_ms=10,
    )

    test_case.assertions = [
        ToolCallsAssertion(type="tool_calls", calls={"my_tool": ToolCallAssertion(called=False)})
    ]
    evaluator = DefaultEvaluator(config)
    metrics = evaluator.eval_test_case(test_case, plan, plan_run, metadata)
    assert metrics
    assert len(metrics) == 1
    m = metrics[0]
    assert m.name == "tool_calls"
    assert m.expectation == ["my_tool"]
    assert isinstance(m.actual_value, list)
    assert "my_tool" in m.actual_value


def test_tool_calls_no_assertion(config: Config, test_case: EvalTestCase) -> None:
    """Test outcomes."""
    plan, plan_run = get_test_plan_run()
    metadata = PlanRunMetadata(
        tool_calls=[],
        latency_ms=10,
    )

    test_case.assertions = [ToolCallsAssertion(type="tool_calls", calls={})]
    evaluator = DefaultEvaluator(config)
    metrics = evaluator.eval_test_case(test_case, plan, plan_run, metadata)
    assert metrics
    assert len(metrics) == 1
    m = metrics[0]
    assert m.name == "tool_calls"
    assert m.expectation == []


def test_tool_calls_no_call_assertion(config: Config, test_case: EvalTestCase) -> None:
    """Test outcomes."""
    plan, plan_run = get_test_plan_run()
    metadata = PlanRunMetadata(
        tool_calls=[],
        latency_ms=10,
    )

    test_case.assertions = [
        ToolCallsAssertion(type="tool_calls", calls={"my_tool": ToolCallAssertion(called=True)})
    ]
    evaluator = DefaultEvaluator(config)
    metrics = evaluator.eval_test_case(test_case, plan, plan_run, metadata)
    assert metrics
    assert len(metrics) == 1
    m = metrics[0]
    assert m.name == "tool_calls"
    assert m.expectation == ["my_tool"]


@patch("steelthread.evals.default_evaluator.LLMMetricScorer")
def test_final_output_llm_judge(
    mock_scorer_class: LLMMetricScorer, config: Config, test_case: EvalTestCase
) -> None:
    """Test outcomes."""
    plan, plan_run = get_test_plan_run()
    metadata = PlanRunMetadata(
        tool_calls=[],
        latency_ms=10,
    )

    # Fake output value
    plan_run.outputs.final_output = LocalDataValue(value="actual result")

    # Add LLM-based final_output assertion
    test_case.assertions = [
        FinalOutputAssertion(
            type="final_output",
            output_type="llm_judge",
            value="expected result",
        )
    ]

    mock_metric = MetricOnly(
        name="final_output",
        description="LLM-based final output score",
        score=0.8,
        explanation="LLM says it's close enough",
    )
    mock_scorer = mock_scorer_class.return_value  # type: ignore  # noqa: PGH003
    mock_scorer.score.return_value = [mock_metric]

    evaluator = DefaultEvaluator(config)
    metrics = evaluator.eval_test_case(test_case, plan, plan_run, metadata)
    assert metrics
    assert len(metrics) == 1
    m = metrics[0]
    assert m.name == "final_output"
    assert m.score == 0.8
    assert m.expectation == "expected result"
    assert m.actual_value == "actual result"
    assert m.description == "LLM-based final output score"
    assert m.explanation == "LLM says it's close enough"

    # Check LLMMetricScorer was called correctly
    mock_scorer_class.assert_called_once_with(config)  # type: ignore  # noqa: PGH003
