"""Main runner for steel thread."""

from portia import Portia

from steelthread.evals import EvalConfig, EvalRunner
from steelthread.streams import StreamConfig, StreamProcessor


class SteelThread:
    """Main steel thread runner.

    Provides static methods to run both stream and evaluation based workflows.
    """

    @staticmethod
    def process_stream(config: StreamConfig) -> None:
        """Process stream items based on the config given.

        Args:
            config (EvalConfig): Configuration for stream processor.

        """
        StreamProcessor(config).run()

    @staticmethod
    def run_evals(portia: Portia, config: EvalConfig) -> None:
        """Run evaluations using Portia and the provided configuration.

        Args:
            portia (Portia): Portia instance used for model access and execution.
            config (EvalConfig): Configuration for evaluation runs.

        """
        EvalRunner(portia, config).run()
