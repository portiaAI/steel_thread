"""Example evals runs."""

import re

from portia import (
    Config,
    DefaultToolRegistry,
    LogLevel,
    Plan,
    PlanRun,
    Portia,
)

from steelthread.evals import (
    DefaultEvaluator,
    EvalConfig,
    EvalMetric,
    EvalTestCase,
    Evaluator,
    PlanRunMetadata,
)
from steelthread.portia.tools import ToolStubContext, ToolStubRegistry
from steelthread.steelthread import (
    SteelThread,
)
from steelthread.streams import StreamConfig

# Requires:
# OPENWEATHERMAP_API_KEY
# LLM Key set i.e. OPENAI_API_KEY
# PORTIA_API_KEY


# Setup config + Steel Thread
config = Config.from_default(
    default_log_level=LogLevel.CRITICAL,
)
st = SteelThread()


# Process stream
st.process_stream(
    StreamConfig(stream_name="stream_v2", config=config, additional_tags={"feeling": "neutral"})
)

# Run evals
portia = Portia(config)
st.run_evals(
    portia,
    EvalConfig(
        eval_dataset_name="evals_v1",
        config=config,
        iterations=4,
    ),
)


# Define a custom evaluator
class EmojiEvaluator(Evaluator):
    """Evaluator that scores on emoji use."""

    def eval_test_case(
        self,
        test_case: EvalTestCase,
        final_plan: Plan,  # noqa: ARG002
        final_plan_run: PlanRun,
        additional_data: PlanRunMetadata,  # noqa: ARG002
    ) -> list[EvalMetric] | EvalMetric | None:
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

        expected_emojis = int(test_case.get_custom_assertion("expected_emojis") or 2)

        score = min(emoji_count / int(expected_emojis), 1.0)  # 0.0 to 1.0 scale

        return EvalMetric(
            score=score,
            name="final_output_emoji_count",
            description=f"Scores highly when number of emojis > {expected_emojis}",
            dataset=test_case.dataset,
            testcase=test_case.testcase,
            run=test_case.run,
            expectation=str(expected_emojis),
            actual_value=str(emoji_count),
        )


# Define a tool stub
def weather_stub_response(
    ctx: ToolStubContext,
) -> str:
    """Stub for weather tool to return deterministic weather."""
    city = ctx.kwargs.get("city", "").lower()
    if city == "sydney":
        return "33.28"
    if city == "london":
        return "2.00"

    return f"Unknown city: {city}"


# Run evals with stubs + custom evaluators.
portia = Portia(
    config,
    tools=ToolStubRegistry(
        DefaultToolRegistry(config),
        stubs={
            "weather_tool": weather_stub_response,
        },
    ),
)
st.run_evals(
    portia,
    EvalConfig(
        eval_dataset_name="evals_v1",
        config=config,
        iterations=1,
        evaluators=[DefaultEvaluator(config), EmojiEvaluator(config)],
    ),
)
