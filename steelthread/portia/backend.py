"""Backend for Portia evals."""

import httpx
from portia import Config
from portia.storage import PortiaCloudClient
from pydantic import BaseModel

from steelthread.offline_evaluators.test_case import OfflineTestCase
from steelthread.online_evaluators.test_case import OnlineTestCase


class PortiaBackend(BaseModel):
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

    def load_online_evals(self, data_set: str) -> list[OnlineTestCase]:
        """Load online test cases from the Portia API.

        Args:
            data_set (str): The dataset name to fetch test cases for.

        Returns:
            list[OnlineTestCase]: A list of parsed online test cases.

        """
        client = self.client()
        response = client.get(
            url=f"/api/v0/evals/test-cases/?dataset_name={data_set}",
        )
        self.check_response(response)
        response_json = response.json()
        test_cases = []
        for tc in response_json:
            ds = OnlineTestCase(**tc)
            test_cases.append(ds)
        return test_cases

    def load_offline_evals(self, data_set: str) -> list[OfflineTestCase]:
        """Load offline test cases from the Portia API.

        Args:
            data_set (str): The dataset name to fetch test cases for.

        Returns:
            list[OfflineTestCase]: A list of parsed offline test cases.

        """
        client = self.client()
        response = client.get(
            url=f"/api/v0/evals/test-cases/?dataset_name={data_set}",
        )
        self.check_response(response)
        response_json = response.json()
        test_cases = []
        for tc in response_json:
            ds = OfflineTestCase(**tc)
            test_cases.append(ds)
        return test_cases

    def mark_processed(self, tc: OnlineTestCase) -> None:
        """Mark an online test case as processed in the Portia API.

        Args:
            tc (OnlineTestCase): The test case to mark as processed.

        """
        client = self.client()
        response = client.patch(
            url="/api/v0/evals/test-cases/",
            json={"processed": True, "id": tc.id},
        )
        self.check_response(response)
