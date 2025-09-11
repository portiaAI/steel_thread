"""Test timing."""

import threading
import time
from unittest.mock import MagicMock, patch

from steelthread.utils.timing import EventTimer


def test_timing() -> None:
    """Test format only."""
    timer = EventTimer(total_events=1)
    timer.record_timing_seconds(120, update_display=False)
    assert timer._pretty(120) == "2m 00s"


def test_pretty_formatting() -> None:
    """Test pretty formatting for various durations."""
    timer = EventTimer(total_events=1)

    # Test seconds only
    assert timer._pretty(45) == "45s"
    assert timer._pretty(0) == "0s"
    assert timer._pretty(59) == "59s"

    # Test minutes and seconds
    assert timer._pretty(60) == "1m 00s"
    assert timer._pretty(125) == "2m 05s"
    assert timer._pretty(3600) == "60m 00s"


def test_event_timer_basic_stats() -> None:
    """Test basic stats functionality."""
    timer = EventTimer(total_events=10)

    # Test initial state
    assert timer.processed == 0
    assert timer.remaining == 10
    assert timer.avg_seconds == 0.0

    # Add some timing data
    timer.record_timing_seconds(2.0, update_display=False)
    timer.record_timing_seconds(4.0, update_display=False)

    assert timer.processed == 2
    assert timer.remaining == 8
    assert timer.avg_seconds == 3.0


def test_event_timer_predictions() -> None:
    """Test prediction functionality."""
    timer = EventTimer(total_events=5)

    # Add timing data
    timer.record_timing_seconds(10.0, update_display=False)
    timer.record_timing_seconds(20.0, update_display=False)

    prediction = timer.predict_end()

    # Average is 15 seconds, 3 remaining events = 45 seconds left
    assert prediction["remaining_seconds"] == 45.0
    assert prediction["remaining_pretty"] == "45s"
    assert "eta" in prediction


def test_record_timing_milliseconds() -> None:
    """Test recording timing in milliseconds."""
    timer = EventTimer(total_events=2)

    result = timer.record_timing_milliseconds(2000, update_display=False)  # 2 seconds
    assert result == 2.0
    assert timer.avg_seconds == 2.0


@patch("steelthread.utils.timing.tqdm")
def test_update_display_with_tqdm(mock_tqdm_class: MagicMock) -> None:
    """Test that update_display creates and updates tqdm progress bar."""
    mock_pbar = MagicMock()
    mock_tqdm_class.return_value = mock_pbar

    timer = EventTimer(total_events=10)
    timer.record_timing_seconds(5.0, update_display=False)

    # Call update_display
    timer.update_display()

    # Check that tqdm was called with correct parameters
    mock_tqdm_class.assert_called_once_with(
        total=10,
        desc="Processing",
        unit="events",
        dynamic_ncols=True,
        leave=True,
    )

    # Check that progress bar was updated
    assert mock_pbar.n == 1  # One event processed
    mock_pbar.set_postfix.assert_called_once()
    mock_pbar.refresh.assert_called_once()


@patch("steelthread.utils.timing.tqdm")
def test_update_display_reuses_existing_pbar(mock_tqdm_class: MagicMock) -> None:
    """Test that update_display reuses existing progress bar."""
    mock_pbar = MagicMock()
    mock_tqdm_class.return_value = mock_pbar

    timer = EventTimer(total_events=5)
    timer.record_timing_seconds(2.0, update_display=False)

    # Call update_display twice
    timer.update_display()
    timer.update_display()

    # tqdm should only be created once
    mock_tqdm_class.assert_called_once()

    # But set_postfix and refresh should be called twice
    assert mock_pbar.set_postfix.call_count == 2
    assert mock_pbar.refresh.call_count == 2


@patch("steelthread.utils.timing.tqdm")
def test_record_timing_with_update_display(mock_tqdm_class: MagicMock) -> None:
    """Test record_timing with update_display=True."""
    mock_pbar = MagicMock()
    mock_tqdm_class.return_value = mock_pbar

    timer = EventTimer(total_events=3)

    # Record timing with display update
    result = timer.record_timing_seconds(10.0, update_display=True)

    assert result == 10.0
    mock_tqdm_class.assert_called_once()
    mock_pbar.set_postfix.assert_called_once()
    mock_pbar.refresh.assert_called_once()


@patch("steelthread.utils.timing.tqdm")
def test_record_timing_milliseconds_with_update_display(mock_tqdm_class: MagicMock) -> None:
    """Test record_timing_milliseconds with update_display=True."""
    mock_pbar = MagicMock()
    mock_tqdm_class.return_value = mock_pbar

    timer = EventTimer(total_events=3)

    # Record timing with display update
    result = timer.record_timing_milliseconds(5000, update_display=True)  # 5 seconds

    assert result == 5.0
    mock_tqdm_class.assert_called_once()
    mock_pbar.set_postfix.assert_called_once()
    mock_pbar.refresh.assert_called_once()


@patch("steelthread.utils.timing.tqdm")
def test_close_progress_bar(mock_tqdm_class: MagicMock) -> None:
    """Test that close method properly closes the progress bar."""
    mock_pbar = MagicMock()
    mock_tqdm_class.return_value = mock_pbar

    timer = EventTimer(total_events=5)
    timer.update_display()  # Create the progress bar

    # Close the progress bar
    timer.close()

    mock_pbar.close.assert_called_once()
    assert timer._pbar is None


@patch("steelthread.utils.timing.tqdm")
def test_close_without_pbar(mock_tqdm_class: MagicMock) -> None:
    """Test that close method handles case where no progress bar exists."""
    timer = EventTimer(total_events=5)

    # Should not raise any exceptions
    timer.close()

    # tqdm should not be created
    mock_tqdm_class.assert_not_called()


def test_threading_safety() -> None:
    """Test that timing operations are thread-safe."""
    timer = EventTimer(total_events=100)
    results = []

    def worker() -> None:
        for _ in range(10):
            result = timer.record_timing_milliseconds(100, update_display=False)
            results.append(result)
            time.sleep(0.001)  # Small delay to allow thread interleaving

    threads = [threading.Thread(target=worker) for _ in range(10)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    # All threads completed
    assert timer.processed == 100
    assert len(results) == 100
