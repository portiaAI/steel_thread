"""Test eval runner."""

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from steelthread.evals.eval_runner import EvalConfig, EvalRunner
from steelthread.evals.metrics import EvalMetric
from steelthread.evals.models import EvalTestCase, InputConfig
from tests.unit.utils import get_test_config, get_test_plan_run


def make_test_case(with_plan: bool) -> EvalTestCase:
    """Make tc."""
    if with_plan:
        (plan, _) = get_test_plan_run()
        return EvalTestCase(
            dataset="ds",
            testcase="tc",
            run="run",
            input_config=InputConfig(type="plan_id", value=str(plan.id)),
            assertions=[],
        )
    return EvalTestCase(
        dataset="ds",
        testcase="tc",
        run="run",
        input_config=InputConfig(type="query", value="do something"),
        assertions=[],
    )


def test_eval_config_defaults() -> None:
    """Test EvalConfig initializes defaults."""
    config = get_test_config()
    eval_config = EvalConfig(eval_dataset_name="test", config=config)
    assert eval_config.iterations == 3
    assert eval_config.max_concurrency == 5
    assert eval_config.evaluators
    assert eval_config.metrics_backends


@patch("steelthread.evals.eval_runner.PortiaBackend")
@patch("steelthread.evals.eval_runner.ThreadPoolExecutor")
@patch("steelthread.evals.eval_runner.as_completed")
def test_eval_runner_run_method(
    mock_as_completed: MagicMock,
    mock_executor_cls: MagicMock,
    mock_backend_cls: MagicMock,
) -> None:
    """Test EvalRunner.run with mocked executor and backend."""
    config = EvalConfig(
        eval_dataset_name="set",
        config=get_test_config(),
        iterations=1,
        metrics_backends=[MagicMock()],
    )

    # Mock Portia engine
    mock_portia = MagicMock()
    runner = EvalRunner(mock_portia, config=config)

    test_case = make_test_case(with_plan=False)
    mock_backend_cls.return_value.load_evals.return_value = [test_case]

    mock_metric = EvalMetric.from_test_case(
        test_case=test_case,
        score=1.0,
        name="clarity",
        description="desc",
        explanation="good metric good eval",
    )

    mock_future = MagicMock()
    mock_future.result.return_value = [mock_metric]
    mock_as_completed.return_value = [mock_future]

    mock_executor = MagicMock()
    mock_executor_cls.return_value.__enter__.return_value = mock_executor
    mock_executor.submit.return_value = mock_future

    runner.run()

    for backend in config.metrics_backends:
        backend.save_eval_metrics.assert_called_once()  # type: ignore  # noqa: PGH003


@patch("steelthread.evals.eval_runner.NoAuthPullPortia")
@patch("steelthread.evals.eval_runner.ReadOnlyStorage")
def test_evaluate_and_collect_metrics(
    mock_storage_cls: MagicMock,  # noqa: ARG001
    mock_portia_cls: MagicMock,
) -> None:
    """Test _evaluate_and_collect_metrics returns tagged metrics."""
    config = EvalConfig(
        eval_dataset_name="dataset",
        config=get_test_config(),
        metrics_backends=[MagicMock()],
    )
    test_case = make_test_case(with_plan=False)

    mock_metric = EvalMetric.from_test_case(
        test_case=test_case,
        score=1.0,
        name="clarity",
        description="desc",
        explanation="enough here",
    )

    mock_evaluator = MagicMock()
    mock_evaluator.eval_test_case.return_value = [mock_metric]
    config.evaluators = [mock_evaluator]  # type: ignore  # noqa: PGH003

    runner = EvalRunner(portia=mock_portia_cls, config=config)
    result = runner._evaluate_and_collect_metrics(test_case)
    assert isinstance(result, list)
    assert result[0].name == "clarity"


@patch("steelthread.evals.eval_runner.PlanUUID.from_string")
def test_run_test_case_query_input(mock_plan_uuid: MagicMock) -> None:  # noqa: ARG001
    """Test _run_test_case with input type 'query'."""
    config = EvalConfig(eval_dataset_name="d", config=get_test_config())
    mock_portia = MagicMock()
    mock_plan = MagicMock()
    mock_output = MagicMock()

    mock_portia.plan.return_value = mock_plan
    mock_portia.run_plan.return_value = mock_output

    runner = EvalRunner(portia=mock_portia, config=config)
    test_case = make_test_case(with_plan=False)

    plan, output, latency = runner._run_test_case(test_case, mock_portia)
    assert plan == mock_plan
    assert output == mock_output
    assert isinstance(latency, float)


@patch("steelthread.evals.eval_runner.PlanUUID.from_string")
def test_run_test_case_plan_id_input(mock_plan_uuid: MagicMock) -> None:
    """Test _run_test_case with input type 'plan_id'."""
    config = EvalConfig(eval_dataset_name="d", config=get_test_config())
    mock_portia = MagicMock()
    mock_plan = MagicMock()
    mock_output = MagicMock()

    mock_portia.storage.get_plan.return_value = mock_plan
    mock_portia.run_plan.return_value = mock_output
    mock_plan_uuid.return_value = UUID("11111111-1111-1111-1111-111111111111")

    runner = EvalRunner(portia=mock_portia, config=config)
    test_case = make_test_case(with_plan=True)

    plan, output, latency = runner._run_test_case(test_case, mock_portia)
    assert plan == mock_plan
    assert output == mock_output
    assert isinstance(latency, float)


def test_run_test_case_invalid_type() -> None:
    """Test _run_test_case raises for unknown input type."""
    config = EvalConfig(eval_dataset_name="d", config=get_test_config())
    mock_portia = MagicMock()
    runner = EvalRunner(mock_portia, config=config)

    test_case = make_test_case(with_plan=False)
    test_case.input_config.type = "unknown"  # type: ignore  # noqa: PGH003

    with pytest.raises(ValueError, match="invalid input_config type: unknown"):
        runner._run_test_case(test_case, mock_portia)
