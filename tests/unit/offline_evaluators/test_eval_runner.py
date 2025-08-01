"""Test offline eval runner."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from _pytest.monkeypatch import MonkeyPatch
from portia import Plan, PlanRun
from pydantic import SecretStr

from steelthread.utils.models import EvalRun
from steelthread.tags.offline_metric import Metric, MetricsBackend, MetricWithTag
from steelthread.evals.eval_runner import OfflineEvalConfig, OfflineEvalRunner
from steelthread.evals.evaluator import OfflineEvaluator, PlanRunMetadata
from steelthread.evals.models import InputConfig, OfflineTestCase
from tests.unit.utils import get_test_config


class DummyEvaluator(OfflineEvaluator):
    """Fake evaluator."""

    def eval_test_case(
        self,
        test_case: OfflineTestCase,  # noqa: ARG002
        final_plan: Plan,  # noqa: ARG002
        final_plan_run: PlanRun,  # noqa: ARG002
        additional_data: PlanRunMetadata,  # noqa: ARG002
    ) -> list[Metric] | Metric | None:
        """Return fake metrics."""
        return [Metric(name="dummy", description="desc", score=1.0)]


class RecordingMetricsBackend(MetricsBackend):
    """Records metric save calls."""

    def __init__(self) -> None:
        """Init storage."""
        self.saved = []

    def save_metrics(self, eval_run: EvalRun, metrics: list[MetricWithTag]) -> None:
        """Append to storage."""
        self.saved.append((eval_run, metrics))


def test_offline_eval_runner_with_mocked_portia(monkeypatch: MonkeyPatch) -> None:
    """Test offline with plan run."""
    # Mock Portia
    mock_portia = MagicMock()
    mock_portia.run.return_value = {"result": "success"}
    mock_portia.tool_registry = MagicMock()
    mock_portia.storage = MagicMock()

    # Real config and evaluator
    config = get_test_config(portia_api_key=SecretStr("123"))
    evaluator = DummyEvaluator(config)
    metrics_backend = RecordingMetricsBackend()

    eval_config = OfflineEvalConfig(
        eval_set_name="demo-dataset",
        config=config,
        iterations=1,
        evaluators=[evaluator],
        additional_tags={"env": "test"},
        metrics_backends=[metrics_backend],
    )

    test_case = OfflineTestCase(
        id="123",
        input_config=InputConfig(type="query", value="backflipp"),
        assertions=[],
    )

    # Patch PortiaBackend to return our dummy test case
    monkeypatch.setattr(
        "steelthread.offline_evaluators.eval_runner.PortiaBackend.load_offline_evals",
        lambda self, _: [test_case],  # noqa: ARG005
    )

    runner = OfflineEvalRunner(mock_portia, eval_config)
    runner.run()

    # Assertions
    assert metrics_backend.saved, "Metrics were not saved"
    eval_run, metrics = metrics_backend.saved[0]

    # Each metric should be tagged with env, planning_model, execution_model
    for m in metrics:
        assert isinstance(m.name, str)
        assert m.tags["env"] == "test"
        assert "planning_model" in m.tags
        assert "execution_model" in m.tags


def test_offline_eval_runner_with_mocked_portia_and_plan(monkeypatch: MonkeyPatch) -> None:
    """Test offline with plan."""
    # Mock Portia
    mock_portia = MagicMock()
    mock_portia.run_plan.return_value = {"result": "success"}
    mock_portia.tool_registry = MagicMock()
    mock_portia.storage = MagicMock()

    # Real config and evaluator
    config = get_test_config(portia_api_key=SecretStr("123"))
    evaluator = DummyEvaluator(config)
    metrics_backend = RecordingMetricsBackend()

    eval_config = OfflineEvalConfig(
        eval_set_name="demo-dataset",
        config=config,
        iterations=1,
        evaluators=[evaluator],
        additional_tags={"env": "test"},
        metrics_backends=[metrics_backend],
    )

    test_case = OfflineTestCase(
        id="123",
        input_config=InputConfig(type="plan_id", value=str(uuid4())),
        assertions=[],
    )

    # Patch PortiaBackend to return our dummy test case
    monkeypatch.setattr(
        "steelthread.offline_evaluators.eval_runner.PortiaBackend.load_offline_evals",
        lambda self, _: [test_case],  # noqa: ARG005
    )

    runner = OfflineEvalRunner(mock_portia, eval_config)
    runner.run()

    # Assertions
    assert metrics_backend.saved, "Metrics were not saved"
    eval_run, metrics = metrics_backend.saved[0]

    # Each metric should be tagged with env, planning_model, execution_model
    for m in metrics:
        assert isinstance(m.name, str)
        assert m.tags["env"] == "test"
        assert "planning_model" in m.tags
        assert "execution_model" in m.tags


def test_offline_eval_runner_invalid_input(monkeypatch: MonkeyPatch) -> None:
    """Test with invalid input."""
    # Mock Portia
    mock_portia = MagicMock()
    mock_portia.run_plan.return_value = {"result": "success"}
    mock_portia.tool_registry = MagicMock()
    mock_portia.storage = MagicMock()

    # Real config and evaluator
    config = get_test_config(portia_api_key=SecretStr("123"))
    evaluator = DummyEvaluator(config)
    metrics_backend = RecordingMetricsBackend()

    eval_config = OfflineEvalConfig(
        eval_set_name="demo-dataset",
        config=config,
        iterations=1,
        evaluators=[evaluator],
        additional_tags={"env": "test"},
        metrics_backends=[metrics_backend],
    )

    test_case = OfflineTestCase(
        id="123",
        input_config=InputConfig.model_construct(type="incorrect", value="plan-123"),
        assertions=[],
    )

    # Patch PortiaBackend to return our dummy test case
    monkeypatch.setattr(
        "steelthread.offline_evaluators.eval_runner.PortiaBackend.load_offline_evals",
        lambda self, _: [test_case],  # noqa: ARG005
    )

    runner = OfflineEvalRunner(mock_portia, eval_config)
    with pytest.raises(ValueError):  # noqa: PT011
        runner.run()
