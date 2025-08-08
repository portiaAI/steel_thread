"""Custom Portia instance."""

from portia import Clarification, Plan, PlanRun, Portia


class NoAuthPullPortia(Portia):
    """Override pull auth forward."""

    # to avoid OAuth clarifications which go via the Batch endpoint we return no clarifications here
    # This will defer to the individual tool readiness checks which we can deal with in the Tool.
    def _check_remaining_tool_readiness(
        self,
        plan: Plan,  # noqa: ARG002
        plan_run: PlanRun,  # noqa: ARG002
        start_index: int | None = None,  # noqa: ARG002
    ) -> list[Clarification]:
        return []
