"""Test portia class."""

from portia import InMemoryToolRegistry

from steelthread.portia.portia import NoAuthPullPortia
from tests.unit.utils import get_test_config, get_test_plan_run


def test_no_pull_portia() -> None:
    """Should return no clarifications."""
    portia = NoAuthPullPortia(get_test_config(), tools=InMemoryToolRegistry.from_local_tools([]))
    plan, plan_run = get_test_plan_run()
    clarifications = portia._check_remaining_tool_readiness(plan, plan_run)
    assert len(clarifications) == 0
