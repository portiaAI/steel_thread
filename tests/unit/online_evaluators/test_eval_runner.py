"""Test online eval runner."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from _pytest.monkeypatch import MonkeyPatch
from portia import Plan, PlanRun
from pydantic import SecretStr

from steelthread.common.models import EvalRun
from steelthread.metrics.metric import Metric, MetricsBackend, MetricWithTag
from steelthread.online_evaluators.eval_runner import OnlineEvalConfig, OnlineEvalRunner
from steelthread.online_evaluators.evaluator import OnlineEvaluator
from steelthread.online_evaluators.test_case import OnlineTestCase
from tests.unit.utils import get_test_config, get_test_plan_run


class DummyEvaluator(OnlineEvaluator):
    """Fake evaluator."""

    def eval_plan(self, plan: Plan) -> list[Metric]:  # noqa: ARG002
        """Return metrics."""
        return [Metric(name="plan_metric", description="desc", score=1.0)]

    def eval_plan_run(self, plan_run: PlanRun) -> list[Metric]:  # noqa: ARG002
        """Return metrics."""
        return [Metric(name="plan_run_metric", description="desc", score=0.5)]


class RecordingMetricsBackend(MetricsBackend):
    """Records metric save calls."""

    def __init__(self) -> None:
        """Init storage."""
        self.saved = []

    def save_metrics(self, eval_run: EvalRun, metrics: list[MetricWithTag]) -> None:
        """Append to storage."""
        self.saved.append((eval_run, metrics))


@pytest.fixture
def online_eval_config() -> OnlineEvalConfig:
    """Return config."""
    config = get_test_config(portia_api_key=SecretStr("123"))
    return OnlineEvalConfig(
        data_set_name="test-dataset",
        config=config,
        iterations=1,
        evaluators=[DummyEvaluator(config)],
        additional_tags={"env": "test"},
        metrics_backends=[RecordingMetricsBackend()],
    )


def test_run_with_plan(monkeypatch: MonkeyPatch, online_eval_config: OnlineEvalConfig) -> None:
    """Test run with plan."""
    dummy_test_case = OnlineTestCase(id="", related_item_type="plan", related_item_id=str(uuid4()))
    plan, _ = get_test_plan_run()

    monkeypatch.setattr(
        "steelthread.online_evaluators.eval_runner.PortiaBackend.load_online_evals",
        lambda self, _: [dummy_test_case],  # noqa: ARG005
    )
    monkeypatch.setattr(
        "steelthread.online_evaluators.eval_runner.PortiaCloudStorage.get_plan",
        lambda self, _: plan,  # noqa: ARG005
    )
    monkeypatch.setattr(
        "steelthread.online_evaluators.eval_runner.PortiaCloudStorage.get_plan_run",
        lambda self, _: None,  # noqa: ARG005
    )
    monkeypatch.setattr(
        "steelthread.online_evaluators.eval_runner.PortiaBackend.mark_processed",
        lambda self, tc: None,  # noqa: ARG005
    )

    runner = OnlineEvalRunner(online_eval_config)
    runner.run()

    backend = online_eval_config.metrics_backends[0]
    assert isinstance(backend, RecordingMetricsBackend)
    assert backend.saved
    eval_run, metrics = backend.saved[0]
    assert isinstance(eval_run, EvalRun)
    assert metrics[0].tags["env"] == "test"
    assert "planning_model" in metrics[0].tags


def test_run_with_plan_run(monkeypatch: MonkeyPatch, online_eval_config: OnlineEvalConfig) -> None:
    """Test run plan_run."""
    dummy_test_case = OnlineTestCase(
        id="", related_item_type="plan_run", related_item_id=str(uuid4())
    )
    _, plan_run = get_test_plan_run()

    monkeypatch.setattr(
        "steelthread.online_evaluators.eval_runner.PortiaBackend.load_online_evals",
        lambda self, _: [dummy_test_case],  # noqa: ARG005
    )
    monkeypatch.setattr(
        "steelthread.online_evaluators.eval_runner.PortiaCloudStorage.get_plan_run",
        lambda self, _: plan_run,  # noqa: ARG005
    )
    monkeypatch.setattr(
        "steelthread.online_evaluators.eval_runner.PortiaCloudStorage.get_plan",
        lambda self, _: None,  # noqa: ARG005
    )
    monkeypatch.setattr(
        "steelthread.online_evaluators.eval_runner.PortiaBackend.mark_processed",
        lambda self, tc: None,  # noqa: ARG005
    )

    runner = OnlineEvalRunner(online_eval_config)
    runner.run()

    backend = online_eval_config.metrics_backends[0]
    assert isinstance(backend, RecordingMetricsBackend)
    assert backend.saved
    eval_run, metrics = backend.saved[0]
    assert isinstance(eval_run, EvalRun)
    assert metrics[0].tags["env"] == "test"
    assert "execution_model" in metrics[0].tags


def test_run_skips_invalid_type(
    monkeypatch: MonkeyPatch, online_eval_config: OnlineEvalConfig
) -> None:
    """Test skip invalid."""
    dummy_test_case = OnlineTestCase.model_construct(
        id="", related_item_type="other_thing", related_item_id=str(uuid4())
    )

    monkeypatch.setattr(
        "steelthread.online_evaluators.eval_runner.PortiaBackend.load_online_evals",
        lambda self, _: [dummy_test_case],  # noqa: ARG005
    )
    monkeypatch.setattr(
        "steelthread.online_evaluators.eval_runner.PortiaCloudStorage.get_plan_run",
        lambda self, _: None,  # noqa: ARG005
    )
    monkeypatch.setattr(
        "steelthread.online_evaluators.eval_runner.PortiaCloudStorage.get_plan",
        lambda self, _: None,  # noqa: ARG005
    )
    monkeypatch.setattr(
        "steelthread.online_evaluators.eval_runner.PortiaBackend.mark_processed",
        lambda self, tc: None,  # noqa: ARG005
    )

    runner = OnlineEvalRunner(online_eval_config)
    runner.run()

    backend = online_eval_config.metrics_backends[0]
    assert isinstance(backend, RecordingMetricsBackend)
    assert backend.saved == []  # No metrics saved


def test_run_with_wrong_types(
    monkeypatch: MonkeyPatch, online_eval_config: OnlineEvalConfig
) -> None:
    """Test with wrong types."""
    dummy_test_case = OnlineTestCase(id="", related_item_type="plan", related_item_id=str(uuid4()))

    monkeypatch.setattr(
        "steelthread.online_evaluators.eval_runner.PortiaBackend.load_online_evals",
        lambda self, _: [dummy_test_case],  # noqa: ARG005
    )
    monkeypatch.setattr(
        "steelthread.online_evaluators.eval_runner.PortiaCloudStorage.get_plan",
        lambda self, _: MagicMock(),  # noqa: ARG005
    )
    monkeypatch.setattr(
        "steelthread.online_evaluators.eval_runner.PortiaCloudStorage.get_plan_run",
        lambda self, _: None,  # noqa: ARG005
    )
    monkeypatch.setattr(
        "steelthread.online_evaluators.eval_runner.PortiaBackend.mark_processed",
        lambda self, tc: None,  # noqa: ARG005
    )

    runner = OnlineEvalRunner(online_eval_config)
    with pytest.raises(ValueError):  # noqa: PT011
        runner.run()

    dummy_test_case = OnlineTestCase(
        id="", related_item_type="plan_run", related_item_id=str(uuid4())
    )

    monkeypatch.setattr(
        "steelthread.online_evaluators.eval_runner.PortiaBackend.load_online_evals",
        lambda self, _: [dummy_test_case],  # noqa: ARG005
    )
    monkeypatch.setattr(
        "steelthread.online_evaluators.eval_runner.PortiaCloudStorage.get_plan",
        lambda self, _: None,  # noqa: ARG005
    )
    monkeypatch.setattr(
        "steelthread.online_evaluators.eval_runner.PortiaCloudStorage.get_plan_run",
        lambda self, _: MagicMock(),  # noqa: ARG005
    )
    monkeypatch.setattr(
        "steelthread.online_evaluators.eval_runner.PortiaBackend.mark_processed",
        lambda self, tc: None,  # noqa: ARG005
    )

    runner = OnlineEvalRunner(online_eval_config)
    with pytest.raises(ValueError):  # noqa: PT011
        runner.run()

    dummy_test_case = OnlineTestCase(
        id="", related_item_type="other_item", related_item_id=str(uuid4())
    )
    with pytest.raises(ValueError):  # noqa: PT011
        runner._evaluate(runner.config.evaluators[0], dummy_test_case, MagicMock())
