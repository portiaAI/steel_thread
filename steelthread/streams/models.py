"""Stream Models."""

import enum
from typing import Any

from portia import Plan, PlanRun
from pydantic import BaseModel


class StreamSource(enum.Enum):
    """The source of a stream."""

    PLAN = "plan"
    PLAN_RUN = "plan_run"


class Stream(BaseModel):
    """Definition of a Stream.

    Represents a stream item containing both a plan only.

    Attributes:
         id (str): Unique identifier for the test case.
         plan (Plan): The plan from the StreamItem
         plan_run (PlanRun | None): The plan_run from the StreamItem

    """

    id: str
    name: str
    source: StreamSource
    sample_rate: int
    sample_filters: dict[str, Any]
    last_sampled: str


class PlanStreamItem(BaseModel):
    """Definition of a StreamItem.

    Represents a stream item containing both a plan only.

    Attributes:
         id (str): Unique identifier for the test case.
         plan (Plan): The plan from the StreamItem
         plan_run (PlanRun | None): The plan_run from the StreamItem

    """

    stream: str
    stream_item: str
    plan: Plan


class PlanRunStreamItem(BaseModel):
    """Definition of a PlanRunStreamItem.

    Represents a stream item containing both a plan + plan_run.

    Attributes:
        id (str): Unique identifier for the test case.
        plan (Plan): The plan from the StreamItem
        plan_run (PlanRun): The plan_run from the StreamItem

    """

    stream: str
    stream_item: str
    plan: Plan
    plan_run: PlanRun
