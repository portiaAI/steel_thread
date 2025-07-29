"""Test read only storage."""

from unittest.mock import MagicMock

import pytest
from portia import LocalDataValue, Plan, PlanRun
from portia.portia import EndUser, InMemoryStorage
from portia.storage import ToolCallRecord, ToolCallStatus

from steelthread.portia.storage import ReadOnlyStorage
from tests.unit.utils import get_test_plan_run


@pytest.fixture
def readonly_storage() -> tuple[ReadOnlyStorage, MagicMock, Plan, PlanRun]:
    """Set up storage."""
    plan, plan_run = get_test_plan_run()

    real_storage = MagicMock()
    ro = ReadOnlyStorage(storage=real_storage)
    ro.local_storage = InMemoryStorage()

    ro.local_storage.save_plan(plan)
    ro.local_storage.save_plan_run(plan_run)

    return ro, real_storage, plan, plan_run


def test_get_and_exists_fallback(
    readonly_storage: tuple[ReadOnlyStorage, MagicMock, Plan, PlanRun],
) -> None:
    """Test get and exists."""
    ro, real_storage, plan, plan_run = readonly_storage

    assert ro.get_plan(plan.id) == plan
    assert ro.get_plan_run(plan_run.id) == plan_run
    assert ro.plan_exists(plan.id) is True

    assert ro.get_plan_runs().results == [plan_run]


def test_output_and_tool_call(
    readonly_storage: tuple[ReadOnlyStorage, MagicMock, Plan, PlanRun],
) -> None:
    """Test outputs + tools."""
    ro, _, _, plan_run = readonly_storage

    output = LocalDataValue(value="foo")
    ro.save_plan_run_output("out1", output, plan_run.id)
    assert ro.get_plan_run_output("out1", plan_run.id) == LocalDataValue(value="foo")

    ro.save_tool_call(
        ToolCallRecord(
            tool_name="weather",
            plan_run_id=plan_run.id,
            step=plan_run.current_step_index,
            end_user_id="",
            status=ToolCallStatus.SUCCESS,
            input={},
            output={},
            latency_seconds=1,
        )
    )


def test_similar_plan_proxy(
    readonly_storage: tuple[ReadOnlyStorage, MagicMock, Plan, PlanRun],
) -> None:
    """Test similar plan."""
    ro, real_storage, *_ = readonly_storage
    real_storage.get_similar_plans.return_value = ["dummy"]
    assert ro.get_similar_plans("query") == ["dummy"]
    real_storage.get_similar_plans.assert_called_once()


def test_end_user_proxy(readonly_storage: tuple[ReadOnlyStorage, MagicMock, Plan, PlanRun]) -> None:
    """Test end user."""
    ro, real_storage, *_ = readonly_storage
    user = EndUser(external_id="u1", additional_data={"x": "y"})
    ro.save_end_user(user)
    assert ro.get_end_user("u1") == user


def test_fallback_on_exception(
    readonly_storage: tuple[ReadOnlyStorage, MagicMock, Plan, PlanRun],
) -> None:
    """Test error fallback."""
    ro, real_storage, _, _ = readonly_storage
    ro.local_storage.get_plan_by_query = MagicMock(side_effect=Exception("fail"))
    real_storage.get_plan_by_query.return_value = "fallback"
    assert ro.get_plan_by_query("q") == "fallback"


def test_get_plan_by_query_fallback(
    readonly_storage: tuple[ReadOnlyStorage, MagicMock, Plan, PlanRun],
) -> None:
    """Test get plan by query."""
    ro, real_storage, *_ = readonly_storage
    ro.local_storage.get_plan_by_query = MagicMock(side_effect=Exception("fail"))
    real_storage.get_plan_by_query.return_value = "fallback"
    assert ro.get_plan_by_query("q") == "fallback"


def test_plan_exists_fallback(
    readonly_storage: tuple[ReadOnlyStorage, MagicMock, Plan, PlanRun],
) -> None:
    """Test plan exists."""
    ro, real_storage, plan, *_ = readonly_storage
    ro.local_storage.plan_exists = MagicMock(side_effect=Exception("fail"))
    real_storage.plan_exists.return_value = True
    assert ro.plan_exists(plan.id) is True


def test_get_plan_runs_fallback(
    readonly_storage: tuple[ReadOnlyStorage, MagicMock, Plan, PlanRun],
) -> None:
    """Test get plan runs error."""
    ro, real_storage, *_ = readonly_storage
    ro.local_storage.get_plan_runs = MagicMock(side_effect=Exception("fail"))
    real_storage.get_plan_runs.return_value = MagicMock()
    assert ro.get_plan_runs() == real_storage.get_plan_runs.return_value


def test_get_end_user_fallback(
    readonly_storage: tuple[ReadOnlyStorage, MagicMock, Plan, PlanRun],
) -> None:
    """Test get end user."""
    ro, real_storage, *_ = readonly_storage
    ro.local_storage.get_end_user = MagicMock(side_effect=Exception("fail"))
    real_storage.get_end_user.return_value = EndUser(external_id="fallback")
    end_user = ro.get_end_user("some-id")
    assert end_user
    assert end_user.external_id == "fallback"


def test_save_plan_delegates_to_local_storage(
    readonly_storage: tuple[ReadOnlyStorage, MagicMock, Plan, PlanRun],
) -> None:
    """Test save plan."""
    ro, _, plan, _ = readonly_storage

    # Save the plan again
    ro.save_plan(plan)

    # Should now be in local_storage
    assert ro.local_storage.get_plan(plan.id) == plan


def test_get_plan_falls_back_to_storage(
    readonly_storage: tuple[ReadOnlyStorage, MagicMock, Plan, PlanRun],
) -> None:
    """Test save plan fallback."""
    ro, real_storage, plan, _ = readonly_storage

    # Force local_storage to raise
    ro.local_storage.get_plan = MagicMock(side_effect=Exception("boom"))
    # Mock fallback return
    real_storage.get_plan.return_value = plan

    result = ro.get_plan(plan.id)

    assert result == plan
    real_storage.get_plan.assert_called_once_with(plan.id)


def test_save_plan_run_delegates_to_local_storage(
    readonly_storage: tuple[ReadOnlyStorage, MagicMock, Plan, PlanRun],
) -> None:
    """Test save plan delegate."""
    ro, _, _, plan_run = readonly_storage

    # Save the plan run again
    ro.save_plan_run(plan_run)

    # Should now be in local_storage
    retrieved = ro.local_storage.get_plan_run(plan_run.id)
    assert retrieved == plan_run


def test_get_plan_run_falls_back_to_storage(
    readonly_storage: tuple[ReadOnlyStorage, MagicMock, Plan, PlanRun],
) -> None:
    """Test get plan delegate."""
    ro, real_storage, _, plan_run = readonly_storage

    # Cause local_storage to raise
    ro.local_storage.get_plan_run = MagicMock(side_effect=Exception("fail"))
    real_storage.get_plan_run.return_value = plan_run

    result = ro.get_plan_run(plan_run.id)

    assert result == plan_run
    real_storage.get_plan_run.assert_called_once_with(plan_run.id)
