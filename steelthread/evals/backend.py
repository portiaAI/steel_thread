"""Backend for Portia evals."""

import httpx
from portia import Config
from portia.storage import PortiaCloudClient
from pydantic import BaseModel

from steelthread.evals.models import EvalTestCase


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

    def load_evals(self, dataset_name: str, run_id: str) -> list[EvalTestCase]:
        """Load test cases from the Portia API with pagination."""
        client = self.client()
        url = f"/api/v0/evals/dataset-test-cases/?dataset_name={dataset_name}"
        test_cases = []

        while url:
            response = client.get(url)
            self.check_response(response)
            data = response.json()
            test_cases.extend(
                EvalTestCase(**tc, testcase=tc["id"], run=run_id) for tc in data.get("results", [])
            )
            url = data.get("next")

        return test_cases
