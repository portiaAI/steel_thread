"""Tool stubs + registry."""

from collections.abc import Callable
from typing import Any

from portia import (
    Clarification,
    Tool,
    ToolRegistry,
    ToolRunContext,
)
from portia.common import combine_args_kwargs
from portia.tool_call import ToolCallRecord, ToolCallStatus
from pydantic import BaseModel, Field


class ToolStubContext(BaseModel):
    """Context passed to tool stubs."""

    tool_call_index: int
    original_context: ToolRunContext
    original_tool: Tool | None
    args: tuple[Any, ...]
    kwargs: dict[str, Any]


ToolResponseStub = Callable[[ToolStubContext], Any]


class ToolStub(Tool):
    """A tool stub that returns pre-canned data and records tool calls.

    This is useful for testing or evaluating agentic workflows without invoking real tools.

    Attributes:
        child_tool (Tool | None): If set, the stub will defer to this tool for execution.
        return_callable (ToolResponseStub | None): A function used to return fake tool outputs.
        tool_calls (list[ToolCallRecord]): A record of all tool calls made to this stub.

    """

    child_tool: Tool | None = Field(
        default=None,
        description="The child tool. If set output will be fetched from this tool.",
    )
    return_callable: ToolResponseStub | None = Field(
        default=None,
        description="A callable to produce tool outputs. "
        "Takes (call_index, ctx, args, kwargs) as arguments.",
    )
    tool_calls: list[ToolCallRecord] = Field(
        description="A list of all the tool calls this tool has seen."
    )

    def run(
        self,
        ctx: ToolRunContext,
        *args: Any,
        **kwargs: Any,
    ) -> Any:  # noqa: ANN401
        """Run the stub tool and record the call.

        If `child_tool` is provided, it delegates the call.
        If `return_callable` is provided, it uses it to simulate output.
        Otherwise, it raises a RuntimeError.

        Args:
            ctx (ToolRunContext): The tool run context.
            *args (Any): Positional arguments to the tool.
            **kwargs (Any): Keyword arguments to the tool.

        Returns:
            Any: The tool output (either simulated or delegated).

        """
        call_index = len(self.tool_calls)
        tool_call_status = ToolCallStatus.SUCCESS

        if self.return_callable:
            try:
                stub_ctx = ToolStubContext(
                    tool_call_index=call_index,
                    original_context=ctx,
                    args=args,
                    kwargs=kwargs,
                    original_tool=self.child_tool,
                )
                tool_output = self.return_callable(stub_ctx)
            except Exception as e:  # noqa: BLE001
                tool_output = str(e)
                tool_call_status = ToolCallStatus.FAILED
        elif self.child_tool:
            try:
                tool_output = self.child_tool.run(ctx, *args, **kwargs)
            except Exception as e:  # noqa: BLE001
                tool_output = str(e)
                tool_call_status = ToolCallStatus.FAILED
        else:
            raise RuntimeError("ToolStub must have either child_tool or return_callable set.")

        if isinstance(tool_output, Clarification):
            tool_output.plan_run_id = ctx.plan_run.id

        tc = ToolCallRecord(
            tool_name=self.id,
            plan_run_id=ctx.plan_run.id,
            step=ctx.plan_run.current_step_index,
            end_user_id=ctx.end_user.external_id,
            status=tool_call_status,
            input=combine_args_kwargs(*args, **kwargs),
            output=tool_output,
            latency_seconds=0,
        )
        self.tool_calls.append(tc)
        return tool_output


class ToolStubRegistry(ToolRegistry):
    """A registry that allows setting tool stubs while preserving regular tool behavior.

    This is useful for testing: it wraps a real ToolRegistry but replaces some tools
    with stubbed versions that simulate behavior.

    Attributes:
        stubs (dict[str, ToolResponseStub]): A mapping of tool IDs to response stubs.
        stubbed_tools (dict[str, ToolStub]): Cached stubbed tool instances.

    """

    def __init__(self, registry: ToolRegistry, stubs: dict[str, ToolResponseStub]) -> None:
        """Initialize the stub registry.

        Args:
            registry (ToolRegistry): The original registry to wrap.
            stubs (dict[str, ToolResponseStub]): Stub response functions keyed by tool ID.

        """
        super().__init__(registry.get_tools())
        self.stubs = stubs
        self.stubbed_tools: dict[str, ToolStub] = {}

    def get_tool_calls(self, tool_id: str | None = None) -> list[ToolCallRecord]:
        """Get recorded tool calls for a specific stubbed tool or all stubbed tools.

        Args:
            tool_id (str | None): The tool ID to filter by, or None for all.

        Returns:
            list[ToolCallRecord]: A list of tool call records.

        """
        if not tool_id:
            all_calls = []
            for tool_details in self.stubbed_tools.values():
                all_calls.extend(tool_details.tool_calls)
            return all_calls
        if tool_id in self.stubbed_tools:
            return self.stubbed_tools[tool_id].tool_calls
        return []

    def get_tool(self, tool_id: str) -> Tool:
        """Get a stubbed or wrapped tool by ID.

        If the tool has a response stub, a ToolStub is returned that uses it.
        If not, a ToolStub is returned that wraps the original tool.

        Args:
            tool_id (str): The ID of the tool.

        Returns:
            Tool: A stubbed or wrapped tool instance.

        """
        tool = super().get_tool(tool_id)
        if tool.id in self.stubbed_tools:
            return self.stubbed_tools[tool.id]

        if tool_id in self.stubs:
            tool_stub = ToolStub(
                id=tool.id,
                name=tool.name,
                description=tool.description,
                args_schema=tool.args_schema,
                output_schema=tool.output_schema,
                should_summarize=tool.should_summarize,
                return_callable=self.stubs[tool.id],
                tool_calls=[],
            )
        else:
            tool_stub = ToolStub(
                id=tool.id,
                name=tool.name,
                description=tool.description,
                args_schema=tool.args_schema,
                output_schema=tool.output_schema,
                should_summarize=tool.should_summarize,
                child_tool=tool,
                return_callable=None,
                tool_calls=[],
            )

        self.stubbed_tools[tool_id] = tool_stub
        return tool_stub

    def get_tools(self) -> list[Tool]:
        """Get all tools from the registry, replacing them with stubs as needed.

        Returns:
            list[Tool]: A list of stubbed tool instances.

        """
        tools = super().get_tools()
        return [self.get_tool(tool.id) for tool in tools]
