"""Shared models for the package."""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EvalRun(BaseModel):
    """Class to hold common data on a single run of a dataset.

    Attributes:
        id (UUID): Unique identifier for the evaluation run. Defaults to a new UUID.
        data_set_name (str): The name of the dataset used in the evaluation.
        data_set_type (str): The type of dataset (e.g., 'online', 'offline').

    """

    id: UUID = Field(default_factory=lambda: uuid4())
    data_set_name: str
    data_set_type: str
