"""Test tags."""


import pytest

from steelthread.evals.metrics import EvalMetric
from steelthread.evals.models import EvalTestCase, InputConfig
from steelthread.evals.tags import EvalMetricTagger
from tests.unit.utils import get_test_config, get_test_plan_run


@pytest.fixture
def mock_test_case() -> EvalTestCase:
    """Return a dummy EvalTestCase."""
    return EvalTestCase(
        testcase="test-xyz",
        dataset="dataset",
        run="run",
        input_config=InputConfig(type="query", value="do it"),
        assertions=[],
    )


def test_attach_tags_to_single_metric(
    mock_test_case: EvalTestCase,
) -> None:
    """Test that tags are attached correctly to a single EvalMetric."""
    plan, plan_run = get_test_plan_run()
    metric = EvalMetric.from_test_case(
        test_case=mock_test_case,
        score=0.95,
        name="success",
        description="Did it succeed?",
        explanation="It succeeded",
    )

    result = EvalMetricTagger.attach_tags_to_test_case(
        metrics=metric,
        test_case=mock_test_case,
        plan=plan,
        plan_run=plan_run,
        config=get_test_config(),
        additional_tags={"env": "test"},
    )

    assert isinstance(result, list)
    assert len(result) == 1
    tagged = result[0]
    assert tagged.tags["test_case"] == "test-xyz"
    assert tagged.tags["planning_model"] == "o3-mini"
    assert tagged.tags["execution_model"] == "gpt-4.1"
    assert tagged.tags["introspection_model"] == "o4-mini"
    assert tagged.tags["summarizer_model"] == "gpt-4.1"
    assert tagged.tags["env"] == "test"


def test_attach_tags_to_multiple_metrics(mock_test_case: EvalTestCase) -> None:
    """Test that tags are attached correctly to multiple EvalMetrics."""
    plan, plan_run = get_test_plan_run()
    metrics = [
        EvalMetric.from_test_case(
            test_case=mock_test_case,
            score=1.0,
            name="clarity",
            description="",
            explanation="this is a good one",
        ),
        EvalMetric.from_test_case(
            test_case=mock_test_case,
            score=0.8,
            name="accuracy",
            description="",
            explanation="this is an ok one",
        ),
    ]

    result = EvalMetricTagger.attach_tags_to_test_case(
        metrics=metrics,
        test_case=mock_test_case,
        plan=plan,
        plan_run=plan_run,
        config=get_test_config(),
        additional_tags={"env": "prod"},
    )

    assert len(result) == 2
    for m in result:
        assert m.tags["env"] == "prod"
        assert m.tags["planning_model"] == "o3-mini"
