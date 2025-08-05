"""Test models."""

from steelthread.evals.models import (
    CustomAssertion,
    EvalTestCase,
    FinalOutputAssertion,
    InputConfig,
    LatencyAssertion,
    OutcomeAssertion,
    ToolCallAssertion,
    ToolCallsAssertion,
)


def test_input_config_fields() -> None:
    """Test InputConfig with optional fields."""
    config = InputConfig(type="query", value="what is ai?", tools=["search"], end_user_id="user1")
    assert config.type == "query"
    assert config.tools == ["search"]
    assert config.end_user_id == "user1"


def test_outcome_assertion() -> None:
    """Test OutcomeAssertion model."""
    assertion = OutcomeAssertion(type="outcome", value="COMPLETE")
    assert assertion.type == "outcome"
    assert assertion.value == "COMPLETE"


def test_final_output_assertion() -> None:
    """Test FinalOutputAssertion model."""
    assertion = FinalOutputAssertion(
        type="final_output",
        output_type="exact_match",
        value="The final result",
    )
    assert assertion.output_type == "exact_match"
    assert assertion.value == "The final result"


def test_tool_calls_assertion() -> None:
    """Test ToolCallsAssertion model with multiple tools."""
    assertion = ToolCallsAssertion(
        type="tool_calls",
        calls={
            "search": ToolCallAssertion(called=True),
            "math": ToolCallAssertion(called=False),
        },
    )
    assert assertion.calls["search"].called is True
    assert assertion.calls["math"].called is False


def test_latency_assertion() -> None:
    """Test LatencyAssertion model."""
    assertion = LatencyAssertion(type="latency", threshold_ms=1000)
    assert assertion.threshold_ms == 1000


def test_custom_assertion() -> None:
    """Test CustomAssertion model."""
    assertion = CustomAssertion(type="custom", value={"key1": "value1"})
    assert assertion.value["key1"] == "value1"


def test_eval_test_case_get_custom_assertion_found() -> None:
    """Test EvalTestCase.get_custom_assertion when key exists."""
    test_case = EvalTestCase(
        dataset="d1",
        testcase="t1",
        run="r1",
        input_config=InputConfig(type="query", value="do it"),
        assertions=[CustomAssertion(type="custom", value={"tag": "value-tag"})],
    )
    result = test_case.get_custom_assertion("tag")
    assert result == "value-tag"


def test_eval_test_case_get_custom_assertion_not_found() -> None:
    """Test EvalTestCase.get_custom_assertion when key is missing."""
    test_case = EvalTestCase(
        dataset="d1",
        testcase="t2",
        run="r1",
        input_config=InputConfig(type="plan_id", value="p123"),
        assertions=[CustomAssertion(type="custom", value={"other": "not-here"})],
    )
    result = test_case.get_custom_assertion("missing")
    assert result is None


def test_eval_test_case_mixed_assertions() -> None:
    """Test EvalTestCase handles mixed assertion types correctly."""
    test_case = EvalTestCase(
        dataset="d",
        testcase="t",
        run="r",
        input_config=InputConfig(type="query", value="x"),
        assertions=[
            OutcomeAssertion(type="outcome", value="FAILED"),
            LatencyAssertion(type="latency", threshold_ms=300),
        ],
    )
    assert len(test_case.assertions) == 2
    assert isinstance(test_case.assertions[0], OutcomeAssertion)
