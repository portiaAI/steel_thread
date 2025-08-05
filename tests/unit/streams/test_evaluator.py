"""Test stream evaluators."""

from steelthread.streams.evaluator import StreamEvaluator
from steelthread.streams.metrics import StreamMetric
from steelthread.streams.models import PlanRunStreamItem, PlanStreamItem
from tests.unit.utils import get_test_config, get_test_plan_run


class DummyEvaluator(StreamEvaluator):
    """Concrete implementation of StreamEvaluator for testing."""

    def process_plan(self, stream_item: PlanStreamItem) -> list[StreamMetric]:
        """Return score."""
        return [
            StreamMetric.from_stream_item(stream_item, score=10, name="plan_score", description="")
        ]

    def process_plan_run(self, stream_item: PlanRunStreamItem) -> StreamMetric:
        """Return score."""
        return StreamMetric.from_stream_item(
            stream_item, score=10, name="plan_run_score", description=""
        )


def test_process_plan_returns_metric_list() -> None:
    """Test process_plan returns a list of StreamMetric."""
    evaluator = DummyEvaluator(config=get_test_config())
    plan, _ = get_test_plan_run()
    stream_item = PlanStreamItem(stream="123", stream_item="456", plan=plan)
    result = evaluator.process_plan(stream_item)
    assert isinstance(result, list)
    assert isinstance(result[0], StreamMetric)


def test_process_plan_run_returns_metric() -> None:
    """Test process_plan_run returns a StreamMetric."""
    evaluator = DummyEvaluator(config=get_test_config())
    plan, plan_run = get_test_plan_run()
    stream_item = PlanRunStreamItem(stream="123", stream_item="456", plan=plan, plan_run=plan_run)
    result = evaluator.process_plan_run(stream_item)
    assert isinstance(result, StreamMetric)


def test_base_methods() -> None:
    """Test process_plan_run returns a StreamMetric."""

    class MyEvaluator(StreamEvaluator):
        def process_plan(
            self, stream_item: PlanStreamItem
        ) -> list[StreamMetric] | StreamMetric | None:
            return super().process_plan(stream_item)

        def process_plan_run(
            self, stream_item: PlanRunStreamItem
        ) -> list[StreamMetric] | StreamMetric | None:
            return super().process_plan_run(stream_item)

    evaluator = MyEvaluator(config=get_test_config())
    plan, plan_run = get_test_plan_run()

    stream_item = PlanStreamItem(stream="123", stream_item="456", plan=plan)
    assert evaluator.process_plan(stream_item) == []
    stream_item = PlanRunStreamItem(stream="123", stream_item="456", plan=plan, plan_run=plan_run)
    assert evaluator.process_plan_run(stream_item) == []
