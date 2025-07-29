"""Test tool stubs."""

from typing import Never
from unittest.mock import MagicMock

import pytest
from portia import Clarification, ClarificationCategory, ToolRunContext
from portia.portia import EndUser
from portia.tool import Tool

from steelthread.portia.tools import ToolStub, ToolStubRegistry
from tests.unit.utils import get_test_config, get_test_plan_run


@pytest.fixture
def dummy_context() -> ToolRunContext:
    """Get context."""
    plan, plan_run = get_test_plan_run()
    return ToolRunContext(
        plan=plan,
        plan_run=plan_run,
        config=get_test_config(),
        clarifications=[],
        end_user=EndUser(external_id="user-123"),
    )


def test_tool_stub_with_return_callable(dummy_context: ToolRunContext) -> None:
    """Test with callable."""

    def return_callable(index, ctx, args, kwargs) -> str:  # noqa: ANN001, ARG001
        return "result"

    tool = ToolStub(
        id="test-tool",
        name="Test Tool",
        description="Test",
        output_schema=("any", "any"),
        return_callable=return_callable,
        tool_calls=[],
    )

    assert tool.ready(dummy_context).ready
    result = tool.run(dummy_context, 1, x=2)
    assert result == "result"
    assert len(tool.tool_calls) == 1
    assert tool.tool_calls[0].status.name == "SUCCESS"


def test_tool_stub_with_child_tool(dummy_context: ToolRunContext) -> None:
    """Test with child tool."""

    class DummyChildTool(Tool):
        def run(self, ctx, *args, **kwargs) -> str:  # noqa: ANN001, ANN002, ANN003, ARG002
            return "child-result"

    child = DummyChildTool(
        id="child",
        name="Child Tool",
        description="",
        output_schema=("any", "any"),
    )
    tool = ToolStub(
        id="stub",
        name="Stub Tool",
        description="",
        output_schema=("any", "any"),
        child_tool=child,
        tool_calls=[],
    )

    result = tool.run(dummy_context)
    assert result == "child-result"
    assert tool.tool_calls[0].status.name == "SUCCESS"


def test_tool_stub_with_child_tool_error(dummy_context: ToolRunContext) -> None:
    """Test tool child fail."""

    class DummyChildTool(Tool):
        def run(self, ctx, *args, **kwargs) -> Never:  # noqa: ANN001, ANN002, ANN003, ARG002
            raise ValueError("err from child tool")

    child = DummyChildTool(
        id="child",
        name="Child Tool",
        description="",
        output_schema=("any", "any"),
    )
    tool = ToolStub(
        id="stub",
        name="Stub Tool",
        description="",
        output_schema=("any", "any"),
        child_tool=child,
        tool_calls=[],
    )

    result = tool.run(dummy_context)
    assert result == "err from child tool"
    assert tool.tool_calls[0].status.name == "FAILED"


def test_tool_stub_failure_from_callable(dummy_context: ToolRunContext) -> None:
    """Test fail in callable."""

    def failing_callable(index, ctx, args, kwargs) -> Never:  # noqa: ANN001, ARG001
        raise RuntimeError("fail")

    tool = ToolStub(
        id="fail-tool",
        name="Fail Tool",
        description="",
        output_schema=("any", "any"),
        return_callable=failing_callable,
        tool_calls=[],
    )

    result = tool.run(dummy_context)
    assert "fail" in result
    assert tool.tool_calls[0].status.name == "FAILED"


def test_tool_stub_fails_without_child_or_callable(dummy_context: MagicMock) -> None:
    """Test fails."""
    tool = ToolStub(
        id="bad-tool",
        name="Bad Tool",
        description="",
        output_schema=("any", "any"),
        tool_calls=[],
    )

    with pytest.raises(RuntimeError, match="must have either child_tool or return_callable"):
        tool.run(dummy_context)


def test_tool_stub_sets_plan_run_id_on_clarification(dummy_context: MagicMock) -> None:
    """Test stub w clarification."""

    def returns_clarification(index, ctx, args, kwargs) -> Clarification:  # noqa: ANN001, ARG001
        return Clarification(
            category=ClarificationCategory.INPUT,
            user_guidance="help",
            plan_run_id=ctx.plan_run.id,
        )

    tool = ToolStub(
        id="clarify-tool",
        name="Clarify Tool",
        description="",
        output_schema=("any", "any"),
        return_callable=returns_clarification,
        tool_calls=[],
    )

    result = tool.run(dummy_context)
    assert isinstance(result, Clarification)
    assert result.plan_run_id == dummy_context.plan_run.id


def test_tool_stub_registry_resolves_stubs() -> None:
    """Test resolving stubs."""

    class DummyChildTool(Tool):
        def run(self, ctx, *args, **kwargs) -> str:  # noqa: ANN001, ANN002, ANN003, ARG002
            return "child-result"

    tool = DummyChildTool(
        id="my-tool",
        name="Tool",
        description="desc",
        output_schema=("any", "any"),
    )

    registry = MagicMock()
    registry.get_tools.return_value = [tool]

    def stub_fn(index, ctx, args, kwargs) -> str:  # noqa: ANN001, ARG001
        return "ok"

    stub_registry = ToolStubRegistry(registry=registry, stubs={"my-tool": stub_fn})
    resolved = stub_registry.get_tool("my-tool")
    assert isinstance(resolved, ToolStub)
    assert resolved.return_callable is stub_fn


def test_tool_stub_registry_fallbacks_and_calls_tracking() -> None:
    """Tool that is not explicitly stubbed."""

    class DummyChildTool(Tool):
        def run(self, ctx, *args, **kwargs) -> str:  # noqa: ANN001, ANN002, ANN003, ARG002
            return "child-result"

    base_tool = DummyChildTool(
        id="base-tool",
        name="Tool",
        description="desc",
        output_schema=("any", "any"),
    )
    registry = MagicMock()
    registry.get_tools.return_value = [base_tool]
    registry.get_tool.return_value = base_tool

    stub_registry = ToolStubRegistry(registry=registry, stubs={})

    resolved = stub_registry.get_tool("base-tool")
    assert isinstance(resolved, ToolStub)
    assert resolved.child_tool == base_tool

    calls = stub_registry.get_tool_calls("base-tool")
    assert calls == []

    calls = stub_registry.get_tool_calls("other-tool")
    assert calls == []

    all_calls = stub_registry.get_tool_calls()
    assert isinstance(all_calls, list)

    def stub_response(index: int, ctx: ToolRunContext, args: tuple, kwargs: dict) -> str:  # noqa: ARG001
        return "stub"

    stub_registry = ToolStubRegistry(registry=registry, stubs={"base-tool": stub_response})

    # should cache tool stubs
    resolved1 = stub_registry.get_tool("base-tool")
    assert isinstance(resolved, ToolStub)
    resolved2 = stub_registry.get_tool("base-tool")
    assert isinstance(resolved, ToolStub)
    assert resolved1 == resolved2

    tools = stub_registry.get_tools()
    assert isinstance(tools, list)
