"""Test main class."""

from unittest.mock import Mock, patch

from steelthread.steelthread import SteelThread


def test_run_evals() -> None:
    """Test run evals."""
    mock_portia = Mock()
    mock_config = Mock()

    with patch("steelthread.steelthread.EvalRunner") as mock_runner:
        mock_runner_instance = mock_runner.return_value
        SteelThread.run_evals(mock_portia, mock_config)

        mock_runner.assert_called_once_with(mock_portia, mock_config)
        mock_runner_instance.run.assert_called_once()


def test_process_stream() -> None:
    """Test process stream."""
    mock_config = Mock()

    with patch("steelthread.steelthread.StreamProcessor") as mock_runner:
        mock_runner_instance = mock_runner.return_value
        SteelThread.process_stream(mock_config)

        mock_runner.assert_called_once_with(mock_config)
        mock_runner_instance.run.assert_called_once()
