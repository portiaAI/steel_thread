"""Common test utils."""

from portia import (
    Config,
    LocalDataValue,
    LogLevel,
    Plan,
    PlanContext,
    PlanRun,
    Step,
    StorageClass,
    Variable,
)
from pydantic import SecretStr


def get_test_config(**kwargs) -> Config:  # noqa: ANN003
    """Get test config."""
    return Config.from_default(
        **kwargs,
        default_log_level=LogLevel.INFO,
        openai_api_key=SecretStr("123"),
        storage_class=StorageClass.MEMORY,
        llm_redis_cache_url=None,
    )


def get_test_plan_run() -> tuple[Plan, PlanRun]:
    """Generate a simple test plan_run."""
    step1 = Step(
        task="Add $a + 2",
        inputs=[
            Variable(name="$a", description="the first number"),
        ],
        output="$sum",
    )
    plan = Plan(
        plan_context=PlanContext(
            query="Add $a + 2",
            tool_ids=["add_tool"],
        ),
        steps=[step1],
    )
    plan_run = PlanRun(plan_id=plan.id, current_step_index=0, end_user_id="test")
    plan_run.outputs.step_outputs = {
        "$a": LocalDataValue(value="3"),
    }
    return plan, plan_run
