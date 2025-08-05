"""Test evaluator."""

from portia import Plan, PlanRun
from portia.storage import ToolCallRecord, ToolCallStatus

from steelthread.evals.evaluator import Evaluator, PlanRunMetadata
from steelthread.evals.metrics import EvalMetric
from steelthread.evals.models import EvalTestCase, InputConfig
from tests.unit.utils import get_test_config, get_test_plan_run


def test_plan_run_metadata_model() -> None:
    """Test PlanRunMetadata model instantiation."""
    plan, plan_run = get_test_plan_run()
    metadata = PlanRunMetadata(
        tool_calls=[
            ToolCallRecord(
                input="x",
                output="y",
                tool_name="tool",
                plan_run_id=plan_run.id,
                step=1,
                end_user_id="",
                status=ToolCallStatus.SUCCESS,
                latency_seconds=2,
            )
        ],
        latency_ms=123.45,
    )
    assert isinstance(metadata.tool_calls, list)
    assert metadata.latency_ms == 123.45


def test_evaluator_base_class_instantiation() -> None:
    """Test Evaluator base class can be subclassed and used."""

    class DummyEvaluator(Evaluator):
        def eval_test_case(
            self,
            test_case: EvalTestCase,  # noqa: ARG002
            final_plan: Plan,  # noqa: ARG002
            final_plan_run: PlanRun,  # noqa: ARG002
            additional_data: PlanRunMetadata,  # noqa: ARG002
        ) -> list[EvalMetric]:
            return []

    config = get_test_config()
    evaluator = DummyEvaluator(config=config)
    assert evaluator.config is config


def test_base_evaluator_default_method_returns_empty_list() -> None:
    """Test base class default eval_test_case returns empty list."""

    class DummyEvaluator(Evaluator):
        def eval_test_case(
            self,
            test_case: EvalTestCase,
            final_plan: Plan,
            final_plan_run: PlanRun,
            additional_data: PlanRunMetadata,
        ) -> list[EvalMetric] | EvalMetric | None:
            return super().eval_test_case(test_case, final_plan, final_plan_run, additional_data)

    config = get_test_config()
    evaluator = DummyEvaluator(config=config)

    test_case = EvalTestCase(
        dataset="d",
        testcase="t",
        run="r",
        input_config=InputConfig(type="query", value="test"),
        assertions=[],
    )
    plan, plan_run = get_test_plan_run()
    metadata = PlanRunMetadata(tool_calls=[], latency_ms=50.0)

    result = evaluator.eval_test_case(test_case, plan, plan_run, metadata)
    assert result == []
