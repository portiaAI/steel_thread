"""Test stream processor."""

from unittest.mock import MagicMock, patch

import pytest

from steelthread.streams.metrics import StreamMetric
from steelthread.streams.models import PlanRunStreamItem, PlanStreamItem, Stream, StreamSource
from steelthread.streams.stream_processor import StreamConfig, StreamProcessor
from tests.unit.utils import get_test_config, get_test_plan_run


def test_stream_config_defaults() -> None:
    """Test StreamConfig applies defaults correctly."""
    config = get_test_config()
    stream_config = StreamConfig(stream_name="s", config=config)
    assert stream_config.max_concurrency == 5
    assert stream_config.batch_size == 10
    assert len(stream_config.evaluators) == 1
    assert len(stream_config.metrics_backends) == 2


@patch("steelthread.streams.stream_processor.PortiaStreamBackend")
@patch("steelthread.streams.stream_processor.PortiaCloudStorage")
def test_run_with_invalid_source(
    mock_storage: MagicMock,  # noqa: ARG001
    mock_backend: MagicMock,
) -> None:
    """Test run() raises error on invalid source type."""
    config = StreamConfig(stream_name="s", config=get_test_config())
    processor = StreamProcessor(config=config)

    mock_backend.return_value.get_stream.return_value = Stream.model_construct(
        id="123",
        name="s",
        source="StreamSource.PLAN",  # type: ignore  # noqa: PGH003
        sample_filters={},
        sample_rate=100,
        last_sampled="",
    )

    with pytest.raises(ValueError, match="invalid source"):
        processor.run()


@patch("steelthread.streams.stream_processor.PortiaStreamBackend")
@patch("steelthread.streams.stream_processor.PortiaCloudStorage")
@patch("steelthread.streams.stream_processor.StreamMetricTagger.attach_tags")
def test_process_plan_and_save_metrics(
    mock_attach_tags: MagicMock,
    mock_storage: MagicMock,  # noqa: ARG001
    mock_backend: MagicMock,
) -> None:
    """Test plan items are processed and metrics saved."""
    config = StreamConfig(stream_name="s", config=get_test_config())

    # Prepare test item
    plan, _ = get_test_plan_run()
    mock_item = PlanStreamItem(stream="s", stream_item="1", plan=plan)
    mock_backend.return_value.get_stream.return_value = Stream(
        id="123",
        name="s",
        source=StreamSource.PLAN,
        sample_filters={},
        sample_rate=100,
        last_sampled="",
    )
    mock_backend.return_value.load_plan_stream_items.return_value = [mock_item]

    # Provide fake evaluator + metric
    mock_metric = StreamMetric(
        stream="s",
        stream_item="1",
        score=1.0,
        name="test",
        description="desc",
        explanation="ok this is a good metric",
    )
    mock_attach_tags.return_value = [mock_metric]

    mock_evaluator = MagicMock()
    mock_evaluator.process_plan.return_value = [mock_metric]
    config.evaluators = [mock_evaluator]  # type: ignore  # noqa: PGH003
    config.metrics_backends = [  # type: ignore  # noqa: PGH003
        MagicMock(),
    ]

    processor = StreamProcessor(config=config)
    processor.run()

    # Should mark the item and save metrics
    mock_backend.return_value.mark_processed.assert_called_once()
    for backend in config.metrics_backends:
        backend.save_metrics.assert_called_once()  # type: ignore  # noqa: PGH003


@patch("steelthread.streams.stream_processor.PortiaStreamBackend")
@patch("steelthread.streams.stream_processor.PortiaCloudStorage")
@patch("steelthread.streams.stream_processor.StreamMetricTagger.attach_tags")
def test_process_plan_run_integration_style(
    mock_attach_tags: MagicMock,
    mock_storage: MagicMock,  # noqa: ARG001
    mock_backend: MagicMock,
) -> None:
    """Run the real ThreadPoolExecutor (no mocking), just mock I/O and evaluators."""
    config = StreamConfig(stream_name="s", config=get_test_config())

    # Provide one test case
    plan, plan_run = get_test_plan_run()
    item = PlanRunStreamItem(stream="s", stream_item="2", plan=plan, plan_run=plan_run)
    mock_backend.return_value.get_stream.return_value = Stream(
        id="123",
        name="s",
        source=StreamSource.PLAN_RUN,
        sample_filters={},
        sample_rate=100,
        last_sampled="",
    )
    mock_backend.return_value.load_plan_run_stream_items.return_value = [item]

    # Provide fake metrics
    metric = StreamMetric(
        stream="s",
        stream_item="2",
        score=1.0,
        name="clarity",
        description="",
        explanation="good outcome is good",
    )
    mock_attach_tags.return_value = [metric]

    # Patch the evaluators `process_plan_run` to avoid real computation
    mock_evaluator = MagicMock()
    mock_evaluator.process_plan_run.return_value = [metric]

    # Replace default StreamConfig evaluators with our mock
    config.evaluators = [mock_evaluator]  # type: ignore  # noqa: PGH003
    config.metrics_backends = [MagicMock()]  # type: ignore  # noqa: PGH003
    processor = StreamProcessor(config)
    processor.run()

    mock_backend.return_value.mark_processed.assert_called_once()
    for backend in config.metrics_backends:
        backend.save_metrics.assert_called_once()  # type: ignore  # noqa: PGH003
