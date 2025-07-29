"""Online Test Case."""

from pydantic import BaseModel


class OnlineTestCase(BaseModel):
    """Definition of an online test case.

    Represents a test case linked to an existing plan or plan run in the system.

    Attributes:
        id (str): Unique identifier for the test case.
        related_item_id (str): ID of the associated plan or plan run.
        related_item_type (str): Type of the related object ("plan" or "plan_run").

    """

    id: str
    related_item_id: str
    related_item_type: str
