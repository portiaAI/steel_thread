"""Models for test cases."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class InputConfig(BaseModel):
    """Configuration for test case input.

    Attributes:
        type (Literal["query", "plan_id"]): The type of input used (query or plan ID).
        value (str): The actual query string or plan ID.
        tools (list[str] | None): Optional list of tools to be used during execution.
        end_user_id (str | None): Optional ID of the end user to simulate context.

    """

    type: Literal["query", "plan_id"]
    value: str
    tools: list[str] | None = None
    end_user_id: str | None = None


class OutcomeAssertion(BaseModel):
    """Assertion for verifying the outcome state of a plan run.

    Attributes:
        type (Literal["outcome"]): Discriminator for the assertion type.
        value (str): Expected plan run state (e.g., "COMPLETE", "FAILED").

    """

    type: Literal["outcome"]
    value: str


class FinalOutputAssertion(BaseModel):
    """Assertion for verifying the final output content.

    Attributes:
        type (Literal["final_output"]): Discriminator for the assertion type.
        output_type (Literal["exact_match", "partial_match", "llm_judge"]): How to eval the output.
        value (str): Expected final output value.

    """

    type: Literal["final_output"]
    output_type: Literal["exact_match", "partial_match", "llm_judge"]
    value: str


class ToolCallAssertion(BaseModel):
    """Assertion record for whether a specific tool was called.

    Attributes:
        called (bool): Whether the tool was expected to be called.

    """

    called: bool


class ToolCallsAssertion(BaseModel):
    """Assertion for verifying calls to tools.

    Attributes:
        type (Literal["tool_calls"]): Discriminator for the assertion type.
        calls (dict[str, ToolCallAssertion]): Mapping of tool names to expected call status.

    """

    type: Literal["tool_calls"]
    calls: dict[str, ToolCallAssertion]


class LatencyAssertion(BaseModel):
    """Assertion for validating runtime latency.

    Attributes:
        type (Literal["latency"]): Discriminator for the assertion type.
        threshold_ms (float): Acceptable maximum latency in milliseconds.

    """

    type: Literal["latency"]
    threshold_ms: float


class LLMAsJudgeAssertion(BaseModel):
    """Assertion for general LLM as judge.

    Attributes:
        type (Literal["llm_as_judge"]): Discriminator for the assertion type.
        value (str): Expected final output value.

    """

    type: Literal["llm_as_judge"]
    value: str


class CustomAssertion(BaseModel):
    """User-defined assertion with arbitrary key-value metadata.

    Attributes:
        type (Literal["custom"]): Discriminator for the assertion type.
        value (dict[str, str]): Arbitrary assertion data.

    """

    type: Literal["custom"]
    value: dict[str, str]


# Discriminated union of all assertion types
Assertion = Annotated[
    OutcomeAssertion
    | FinalOutputAssertion
    | ToolCallsAssertion
    | LatencyAssertion
    | LLMAsJudgeAssertion
    | CustomAssertion,
    Field(discriminator="type"),
]


class EvalTestCase(BaseModel):
    """Model representing an  test case.

    Attributes:
        id (str): Unique identifier for the test case.
        input_config (InputConfig): Configuration for how to run the test.
        assertions (list[Assertion]): Assertions to validate after execution.

    """

    dataset: str
    testcase: str
    run: str
    input_config: InputConfig
    assertions: list[Assertion]

    def get_custom_assertion(self, key: str) -> str | None:
        """Return the value of a custom assertion by key, if it exists.

        Args:
            key (str): Key to search for in the custom assertions.

        Returns:
            str | None: The value if found, otherwise None.

        """
        for assertion in self.assertions:
            if assertion.type == "custom" and key in assertion.value:
                return assertion.value[key]
        return None
