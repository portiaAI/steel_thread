"""Example evals runs."""

from portia import Config, LogLevel, Portia

from steelthread.evals.eval_runner import EvalConfig
from steelthread.steelthread import (
    SteelThread,
)
from steelthread.streams.stream_processor import StreamConfig

# Setup config + Steel Thread
config = Config.from_default(default_log_level=LogLevel.CRITICAL)
st = SteelThread()


# Run online evals
# st.process_stream(StreamConfig(stream_name="stream_v1", config=config))  # noqa: ERA001

# Run offline evals
portia = Portia(config)
st.run_evals(
    portia,
    EvalConfig(
        eval_dataset_name="evals_v1",
        config=config,
        iterations=4,
    ),
)


# # # Define a custom evaluator
# class ErrorQualityEvaluator(OfflineEvaluator):
#     """Offline evaluator that scores on emoji use."""

#     def eval_test_case(
#         self,
#         test_case: OfflineTestCase,
#         final_plan: Plan,  # noqa: ARG002
#         final_plan_run: PlanRun,
#         additional_data: PlanRunMetadata,  # noqa: ARG002
#     ) -> list[Metric] | Metric | None:
#         """Score plan run outputs based on how many emojis they contain."""

#         if final_plan_run.state != failed:
#             return []


#         score final_plan_run.outputs

#         string_to_score = (
#             f"{final_plan_run.outputs.final_output.get_value()}"
#             if final_plan_run.outputs.final_output
#             else ""
#         )
#         emoji_pattern = re.compile(
#             "[\U0001f600-\U0001f64f"  # emoticons
#             "\U0001f300-\U0001f5ff"  # symbols & pictographs
#             "\U0001f680-\U0001f6ff"  # transport & map symbols
#             "\U0001f1e0-\U0001f1ff"  # flags
#             "]+",
#             flags=re.UNICODE,
#         )

#         emojis = emoji_pattern.findall(string_to_score)
#         emoji_count = len(emojis)

#         expected_emojis = test_case.get_custom_assertion("expected_emojis") or 2

#         score = min(emoji_count / int(expected_emojis), 1.0)  # 0.0 to 1.0 scale

#         return Metric(
#             score=score,
#             name="final_output_emoji_count",
#             description=f"Scores highly when number of emojis > {expected_emojis}",
#         )


# # # Define a tool stub
# def weather_stub_response(
#     tool_call_index: int,  # noqa: ARG001
#     ctx: ToolRunContext,  # noqa: ARG001
#     args: tuple,  # noqa: ARG001
#     kwargs: dict,
# ) -> str:
#     """Stub for weather tool to return deterministic weather."""
#     city = kwargs.get("city", "").lower()
#     if city == "sydney":
#         return "33.28"
#     if city == "london":
#         return "2.00"

#     return f"Unknown city: {city}"


# # # # Run offline evals with stubs + custom evaluators.
# portia = Portia(
#     config,
#     tools=ToolStubRegistry(
#         DefaultToolRegistry(config),
#         stubs={
#             "weather_tool": weather_stub_response,
#         },
#     ),
# )
# st.run_offline(
#     portia,
#     OfflineEvalConfig(
#         eval_set_name="offline_evals_v1",
#         config=config,
#         iterations=1,
#         evaluators=[DefaultOfflineEvaluator(config), EmojiEvaluator(config)],
#     ),
# )
