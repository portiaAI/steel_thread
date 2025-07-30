"""Example evals runs."""

import re

from portia import Config, DefaultToolRegistry, LogLevel, Portia, ToolRunContext
from portia.plan_run import PlanRun

from steelthread.metrics.metric import Metric
from steelthread.offline_evaluators.default_evaluator import DefaultOfflineEvaluator
from steelthread.offline_evaluators.evaluator import OfflineEvaluator, PlanRunMetadata
from steelthread.offline_evaluators.test_case import OfflineTestCase
from steelthread.online_evaluators.eval_runner import OnlineEvalConfig
from steelthread.portia.tools import ToolStubRegistry
from steelthread.steelthread import (
    OfflineEvalConfig,
    SteelThread,
)

# Setup config + Steel Thread
config = Config.from_default(default_log_level=LogLevel.CRITICAL)
st = SteelThread()


# Run online evals
st.run_online(OnlineEvalConfig(data_set_name="online_evals_v1", config=config))

# Run offline evals
portia = Portia(config)
st.run_offline(
    portia,
    OfflineEvalConfig(
        data_set_name="offline_evals_v1",
        config=config,
        iterations=4,
    ),
)


# # Define a custom evaluator
class EmojiEvaluator(OfflineEvaluator):
    """Offline evaluator that scores on emoji use."""

    def eval_test_case(
        self,
        test_case: OfflineTestCase,
        final_plan_run: PlanRun,
        additional_data: PlanRunMetadata,  # noqa: ARG002
    ) -> list[Metric] | Metric | None:
        """Score plan run outputs based on how many emojis they contain."""
        string_to_score = (
            f"{final_plan_run.outputs.final_output.get_value()}"
            if final_plan_run.outputs.final_output
            else ""
        )
        emoji_pattern = re.compile(
            "[\U0001f600-\U0001f64f"  # emoticons
            "\U0001f300-\U0001f5ff"  # symbols & pictographs
            "\U0001f680-\U0001f6ff"  # transport & map symbols
            "\U0001f1e0-\U0001f1ff"  # flags
            "]+",
            flags=re.UNICODE,
        )

        emojis = emoji_pattern.findall(string_to_score)
        emoji_count = len(emojis)

        expected_emojis = test_case.get_custom_assertion("expected_emojis") or 2

        score = min(emoji_count / int(expected_emojis), 1.0)  # 0.0 to 1.0 scale

        return Metric(
            score=score,
            name="final_output_emoji_count",
            description=f"Scores highly when number of emojis > {expected_emojis}",
        )


# # Define a tool stub
def weather_stub_response(
    tool_call_index: int,  # noqa: ARG001
    ctx: ToolRunContext,  # noqa: ARG001
    args: tuple,  # noqa: ARG001
    kwargs: dict,
) -> str:
    """Stub for weather tool to return deterministic weather."""
    city = kwargs.get("city", "").lower()
    if city == "sydney":
        return "33.28"
    if city == "london":
        return "2.00"

    return f"Unknown city: {city}"


# # # Run offline evals with stubs + custom evaluators.
portia = Portia(
    config,
    tools=ToolStubRegistry(
        DefaultToolRegistry(config),
        stubs={
            "weather_tool": weather_stub_response,
        },
    ),
)
st.run_offline(
    portia,
    OfflineEvalConfig(
        data_set_name="offline_evals_v1",
        config=config,
        iterations=1,
        evaluators=[DefaultOfflineEvaluator(config), EmojiEvaluator(config)],
    ),
)
