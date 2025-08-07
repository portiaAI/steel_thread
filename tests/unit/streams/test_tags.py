"""Test tags."""

import pytest

from steelthread.streams.metrics import StreamMetric
from steelthread.streams.models import PlanStreamItem
from steelthread.streams.tags import StreamMetricTagger
from tests.unit.utils import get_test_plan_run


@pytest.fixture
def stream_item() -> PlanStreamItem:
    """Fixture for a sample stream item."""
    plan, _ = get_test_plan_run()
    return PlanStreamItem(stream="s", stream_item="i", plan=plan)


def test_attach_tags_single_metric(stream_item: PlanStreamItem) -> None:
    """Test that a single StreamMetric is wrapped and tagged."""
    metric = StreamMetric(
        stream="s",
        stream_item="i",
        score=0.1,
        name="clarity",
        description="desc",
        explanation="Some explanation",
    )

    tagged = StreamMetricTagger.attach_tags(metric, stream_item, {"env": "test"})
    assert isinstance(tagged, list)
    assert len(tagged) == 1
    assert tagged[0].tags == {"env": "test"}
    assert tagged[0].score == 0.1


def test_attach_tags_multiple_metrics(stream_item: PlanStreamItem) -> None:
    """Test that a list of StreamMetric is processed and tagged."""
    metric1 = StreamMetric(
        stream="s",
        stream_item="1",
        score=0.3,
        name="clarity",
        description="desc",
        explanation="Explained this well",
    )
    metric2 = StreamMetric(
        stream="s",
        stream_item="2",
        score=0.5,
        name="depth",
        description="desc",
        explanation="Also explained well",
    )

    tagged = StreamMetricTagger.attach_tags([metric1, metric2], stream_item, {"stage": "eval"})
    assert len(tagged) == 2
    for m in tagged:
        assert m.tags == {"stage": "eval"}
