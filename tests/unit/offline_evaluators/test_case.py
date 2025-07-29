"""Tests for offline eval test cases."""

from steelthread.offline_evaluators.test_case import (
    CustomAssertion,
    InputConfig,
    OfflineTestCase,
    OutcomeAssertion,
)


def test_get_custom_assertion_returns_value() -> None:
    """Check get tag."""
    test_case = OfflineTestCase(
        id="test1",
        input_config=InputConfig(type="query", value="Help me"),
        assertions=[
            CustomAssertion(type="custom", value={"my_key": "my_value"}),
            OutcomeAssertion(type="outcome", value="COMPLETE"),
        ],
    )

    assert test_case.get_custom_assertion("my_key") == "my_value"


def test_get_custom_assertion_key_not_found() -> None:
    """Check get tag not found."""
    test_case = OfflineTestCase(
        id="test1",
        input_config=InputConfig(type="query", value="Help me"),
        assertions=[
            CustomAssertion(type="custom", value={"some_other_key": "my_value"}),
            OutcomeAssertion(type="outcome", value="COMPLETE"),
        ],
    )

    assert test_case.get_custom_assertion("missing_key") is None


def test_get_custom_assertion_no_custom_type() -> None:
    """Check no custom assertions."""
    test_case = OfflineTestCase(
        id="test1",
        input_config=InputConfig(type="query", value="Help me"),
        assertions=[
            OutcomeAssertion(type="outcome", value="COMPLETE"),
        ],
    )
    assert test_case.get_custom_assertion("my_key") is None
