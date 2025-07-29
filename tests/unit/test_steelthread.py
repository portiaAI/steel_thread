"""Test main class."""

from unittest.mock import Mock, patch

from steelthread.steelthread import SteelThread


def test_run_online() -> None:
    """Test run online."""
    mock_config = Mock()

    with patch("steelthread.steelthread.OnlineEvalRunner") as mock_runner:
        mock_runner_instance = mock_runner.return_value
        SteelThread.run_online(mock_config)

        mock_runner.assert_called_once_with(mock_config)
        mock_runner_instance.run.assert_called_once()


def test_run_offline() -> None:
    """Test run offline."""
    mock_portia = Mock()
    mock_config = Mock()

    with patch("steelthread.steelthread.OfflineEvalRunner") as mock_runner:
        mock_runner_instance = mock_runner.return_value
        SteelThread.run_offline(mock_portia, mock_config)

        mock_runner.assert_called_once_with(mock_portia, mock_config)
        mock_runner_instance.run.assert_called_once()
