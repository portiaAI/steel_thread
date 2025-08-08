"""Backend for Portia evals."""

import httpx
from portia import (
    Config,
    LocalDataValue,
    Plan,
    PlanRun,
    PlanRunState,
    PlanUUID,
)
from portia.plan_run import PlanRunOutputs, PlanRunUUID
from portia.storage import PortiaCloudClient
from pydantic import BaseModel

from steelthread.streams.models import (
    PlanRunStreamItem,
    PlanStreamItem,
    Stream,
)


class PortiaStreamBackend(BaseModel):
    """Client interface for interacting with the Portia API for evaluations.

    Provides methods to load test cases and mark them as processed.

    Attributes:
        config (Config): The Portia configuration containing API credentials and context.

    """

    config: Config

    def client(self) -> httpx.Client:
        """Create an HTTP client for interacting with the Portia API.

        Returns:
            httpx.Client: A configured HTTP client.

        """
        return PortiaCloudClient().get_client(self.config)

    def check_response(self, response: httpx.Response) -> None:
        """Validate the response from Portia API.

        Args:
            response (httpx.Response): The response from the Portia API to check.

        Raises:
            ValueError: If the response status code indicates an error.

        """
        if not response.is_success:
            error_str = str(response.content)
            raise ValueError(error_str)

    def get_stream(self, stream_name: str) -> Stream:
        """Load information about a stream.

        Args:
            stream_name (str): The name of the stream

        Returns:
            Stream: Information on the stream

        """
        client = self.client()
        url = f"/api/v0/evals/streams/by-name/{stream_name}/"
        response = client.get(url)
        self.check_response(response)
        return Stream(**response.json())

    def load_plan_stream_items(self, stream_id: str, batch_size: int) -> list[PlanStreamItem]:
        """Load stream items from the Portia API with pagination."""
        client = self.client()
        url = f"/api/v0/evals/stream-items/?stream_id={stream_id}"
        test_cases = []

        while url and len(test_cases) < batch_size:
            response = client.get(url)
            self.check_response(response)
            data = response.json()
            for tc in data.get("results", []):
                while len(test_cases) < batch_size:
                    test_cases.append(
                        PlanStreamItem(
                            stream=stream_id,
                            stream_item=tc["id"],
                            plan=Plan(**tc["plan"]),
                        )
                    )
            url = data.get("next")

        return test_cases

    def load_plan_run_stream_items(
        self, stream_id: str, batch_size: int
    ) -> list[PlanRunStreamItem]:
        """Load stream items from the Portia API with pagination."""
        client = self.client()
        url = f"/api/v0/evals/stream-items/?stream_id={stream_id}"
        test_cases = []
        while url and len(test_cases) < batch_size:
            response = client.get(url)
            self.check_response(response)
            data = response.json()
            for tc in data.get("results", []):
                while len(test_cases) < batch_size:
                    test_cases.append(
                        PlanRunStreamItem(
                            stream=stream_id,
                            stream_item=tc["id"],
                            plan=Plan.from_response(tc["plan"]),
                            plan_run=PlanRun(
                                id=PlanRunUUID.from_string(tc["plan_run"]["id"]),
                                plan_id=PlanUUID.from_string(tc["plan_run"]["plan"]["id"]),
                                end_user_id=tc["plan_run"]["end_user"],
                                current_step_index=tc["plan_run"]["current_step_index"],
                                state=PlanRunState(tc["plan_run"]["state"]),
                                outputs=PlanRunOutputs.model_validate(tc["plan_run"]["outputs"]),
                                plan_run_inputs={
                                    key: LocalDataValue.model_validate(value)
                                    for key, value in tc["plan_run"]["plan_run_inputs"].items()
                                },
                            ),
                        )
                    )
            url = data.get("next")

        return test_cases

    def mark_processed(self, item: PlanStreamItem | PlanRunStreamItem) -> None:
        """Mark a stream item as processed in the Portia API.

        Args:
            item (StreamItem): The stream item to mark as processed.

        """
        client = self.client()
        response = client.patch(
            url="/api/v0/evals/stream-items/",
            json={"processed": True, "id": str(item.stream_item)},
        )
        self.check_response(response)
