"""Test online evals base classes."""

from portia import Plan, PlanRun

from steelthread.metrics.metric import Metric
from steelthread.online_evaluators.evaluator import OnlineEvaluator
from tests.unit.utils import get_test_config, get_test_plan_run


def test_eval_base_class() -> None:
    """Test base class."""

    class MyEvaluator(OnlineEvaluator):
        def eval_plan(self, plan: Plan) -> list[Metric] | Metric:
            return super().eval_plan(plan)

        def eval_plan_run(self, plan: Plan, plan_run: PlanRun) -> list[Metric] | Metric | None:
            return super().eval_plan_run(plan, plan_run)

    evaluator = MyEvaluator(get_test_config())

    plan, plan_run = get_test_plan_run()

    metrics = evaluator.eval_plan(plan)
    assert isinstance(metrics, list)
    assert len(metrics) == 0

    metrics = evaluator.eval_plan_run(plan, plan_run)
    assert isinstance(metrics, list)
    assert len(metrics) == 0
