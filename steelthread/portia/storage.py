"""Read only storage."""

from portia import LocalDataValue, Output, Plan, PlanRun, PlanUUID
from portia.plan_run import PlanRunState
from portia.portia import EndUser, InMemoryStorage
from portia.prefixed_uuid import PlanRunUUID
from portia.storage import PlanRunListResponse, Storage, ToolCallRecord


class ReadOnlyStorage(Storage):
    """Gets plans, runs and tool calls from underlying storage, but does not save them.

    Writes are stored only in memory and do not persist to the underlying storage backend.
    Useful for testing, dry runs, or debugging environments.
    """

    def __init__(self, storage: Storage) -> None:
        """Initialize the ReadOnlyStorage instance.

        Args:
            storage (Storage): The underlying storage backend to read from.

        """
        self.storage = storage
        self.local_storage = InMemoryStorage()

    def save_plan(self, plan: Plan) -> None:
        """Save a plan to in-memory storage.

        Args:
            plan (Plan): The plan to save.

        """
        return self.local_storage.save_plan(plan)

    def get_plan(self, plan_id: PlanUUID) -> Plan:
        """Retrieve a plan by ID.

        Args:
            plan_id (PlanUUID): The ID of the plan to fetch.

        Returns:
            Plan: The requested plan.

        """
        try:
            return self.local_storage.get_plan(plan_id)
        except Exception:  # noqa: BLE001
            return self.storage.get_plan(plan_id)

    def get_plan_by_query(self, query: str) -> Plan:
        """Retrieve a plan using a string query.

        Args:
            query (str): Query string to identify a plan.

        Returns:
            Plan: The matching plan.

        """
        try:
            return self.local_storage.get_plan_by_query(query)
        except Exception:  # noqa: BLE001
            return self.storage.get_plan_by_query(query)

    def plan_exists(self, plan_id: PlanUUID) -> bool:
        """Check if a plan exists.

        Args:
            plan_id (PlanUUID): The ID of the plan to check.

        Returns:
            bool: True if the plan exists, False otherwise.

        """
        try:
            return self.local_storage.plan_exists(plan_id)
        except Exception:  # noqa: BLE001
            return self.storage.plan_exists(plan_id)

    def save_plan_run(self, plan_run: PlanRun) -> None:
        """Save a plan run to in-memory storage.

        Args:
            plan_run (PlanRun): The plan run to save.

        """
        return self.local_storage.save_plan_run(plan_run)

    def get_plan_run(self, plan_run_id: PlanRunUUID) -> PlanRun:
        """Retrieve a plan run by ID.

        Args:
            plan_run_id (PlanRunUUID): The ID of the plan run.

        Returns:
            PlanRun: The requested plan run.

        """
        try:
            return self.local_storage.get_plan_run(plan_run_id)
        except Exception:  # noqa: BLE001
            return self.storage.get_plan_run(plan_run_id)

    def get_plan_runs(
        self,
        run_state: PlanRunState | None = None,
        page: int | None = None,
    ) -> PlanRunListResponse:
        """Retrieve a list of plan runs.

        Args:
            run_state (PlanRunState | None): Optional filter by run state.
            page (int | None): Optional pagination.

        Returns:
            PlanRunListResponse: The response containing plan runs.

        """
        try:
            return self.local_storage.get_plan_runs(run_state, page)
        except Exception:  # noqa: BLE001
            return self.storage.get_plan_runs()

    def save_tool_call(self, tool_call: ToolCallRecord) -> None:
        """Save a tool call to in-memory storage.

        Args:
            tool_call (ToolCallRecord): The tool call to record.

        """
        return self.local_storage.save_tool_call(tool_call)

    def save_plan_run_output(
        self,
        output_name: str,
        output: Output,
        plan_run_id: PlanRunUUID,
    ) -> Output:
        """Save an output for a plan run in in-memory storage.

        Args:
            output_name (str): The output key name.
            output (Output): The output value.
            plan_run_id (PlanRunUUID): ID of the related plan run.

        Returns:
            Output: The saved output.

        """
        return self.local_storage.save_plan_run_output(output_name, output, plan_run_id)

    def get_plan_run_output(self, output_name: str, plan_run_id: PlanRunUUID) -> LocalDataValue:
        """Retrieve a plan run output by name and ID.

        Args:
            output_name (str): The output key name.
            plan_run_id (PlanRunUUID): ID of the related plan run.

        Returns:
            LocalDataValue: The retrieved output.

        """
        return self.local_storage.get_plan_run_output(output_name, plan_run_id)

    def get_similar_plans(self, query: str, threshold: float = 0.5, limit: int = 5) -> list[Plan]:
        """Get similar plans from the underlying (read-only) storage.

        Args:
            query (str): Search query to match similar plans.
            threshold (float): Similarity threshold.
            limit (int): Maximum number of results to return.

        Returns:
            list[Plan]: A list of similar plans.

        """
        return self.storage.get_similar_plans(query, threshold, limit)

    def save_end_user(self, end_user: EndUser) -> EndUser:
        """Save an end user in memory.

        Args:
            end_user (EndUser): The end user to save.

        Returns:
            EndUser: The saved user.

        """
        return self.local_storage.save_end_user(end_user)

    def get_end_user(self, external_id: str) -> EndUser | None:
        """Retrieve an end user by external ID.

        Args:
            external_id (str): The external user identifier.

        Returns:
            EndUser | None: The matching user, or None if not found.

        """
        try:
            return self.local_storage.get_end_user(external_id)
        except Exception:  # noqa: BLE001
            return self.storage.get_end_user(external_id)
