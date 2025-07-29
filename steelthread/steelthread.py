"""Main runner for steel thread."""

from portia import Portia

from steelthread.offline_evaluators.eval_runner import OfflineEvalConfig, OfflineEvalRunner
from steelthread.online_evaluators.eval_runner import OnlineEvalConfig, OnlineEvalRunner


class SteelThread:
    """Main steel thread runner.

    Provides static methods to run both online and offline evaluation workflows.
    """

    @staticmethod
    def run_online(config: OnlineEvalConfig) -> None:
        """Run online evaluations using the provided configuration.

        Args:
            config (OnlineEvalConfig): Configuration for online evaluation runs.

        """
        OnlineEvalRunner(config).run()

    @staticmethod
    def run_offline(portia: Portia, config: OfflineEvalConfig) -> None:
        """Run offline evaluations using Portia and the provided configuration.

        Args:
            portia (Portia): Portia instance used for model access and execution.
            config (OfflineEvalConfig): Configuration for offline evaluation runs.

        """
        OfflineEvalRunner(portia, config).run()
