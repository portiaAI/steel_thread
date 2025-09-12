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
    """Test different time formatting scenarios."""
    timer = EventTimer(total_events=1)

    # Test seconds only
    assert timer._pretty(30) == "30s"

    # Test minutes and seconds
    assert timer._pretty(90) == "1m 30s"
    assert timer._pretty(125) == "2m 05s"

    # Test edge cases
    assert timer._pretty(0) == "0s"
    assert timer._pretty(60) == "1m 00s"


def test_event_timer_stats() -> None:
    """Test EventTimer statistics calculations."""
    timer = EventTimer(total_events=5)

    # Initial state
    assert timer.processed == 0
    assert timer.remaining == 5
    assert timer.avg_seconds == 0.0

    # Add some timings
    timer.record_timing_seconds(10, update_display=False)
    assert timer.processed == 1
    assert timer.remaining == 4
    assert timer.avg_seconds == 10.0

    timer.record_timing_seconds(20, update_display=False)
    assert timer.processed == 2
    assert timer.remaining == 3
    assert timer.avg_seconds == 15.0

    timer.record_timing_milliseconds(30000, update_display=False)  # 30 seconds
    assert timer.processed == 3
    assert timer.remaining == 2
    assert timer.avg_seconds == 20.0


def test_predict_end() -> None:
    """Test prediction calculations."""
    timer = EventTimer(total_events=3)

    # Add some timings
    timer.record_timing_seconds(10, update_display=False)
    timer.record_timing_seconds(20, update_display=False)

    prediction = timer.predict_end()

    # Should predict 1 remaining event * 15s avg = 15s remaining
    assert prediction["remaining_seconds"] == 15.0
    assert prediction["remaining_pretty"] == "15s"
    assert "eta" in prediction


@patch("steelthread.utils.timing.tqdm")
def test_display_with_progress_bar(mock_tqdm: MagicMock) -> None:
    """Test progress bar display functionality."""
    mock_pbar = MagicMock()
    mock_tqdm.return_value = mock_pbar

    timer = EventTimer(total_events=3)

    # Test first update (should initialize progress bar)
    timer.record_timing_seconds(10, update_display=True)

    mock_tqdm.assert_called_once_with(
        total=3,
        desc="Processing",
        unit="events",
        dynamic_ncols=True,
        leave=True,
    )
    mock_pbar.set_postfix.assert_called_once()
    mock_pbar.refresh.assert_called_once()

    # Test second update (should reuse existing progress bar)
    mock_tqdm.reset_mock()
    mock_pbar.reset_mock()

    timer.record_timing_seconds(15, update_display=True)

    # Should not create new progress bar
    mock_tqdm.assert_not_called()
    mock_pbar.set_postfix.assert_called_once()
    mock_pbar.refresh.assert_called_once()


@patch("steelthread.utils.timing.tqdm")
def test_display_without_update(mock_tqdm: MagicMock) -> None:
    """Test that progress bar is not created when update_display=False."""
    timer = EventTimer(total_events=3)

    # Record timing without display update
    timer.record_timing_seconds(10, update_display=False)

    # Progress bar should not be initialized
    mock_tqdm.assert_not_called()


@patch("steelthread.utils.timing.tqdm")
def test_display_with_milliseconds(mock_tqdm: MagicMock) -> None:
    """Test progress bar display with milliseconds timing method."""
    mock_pbar = MagicMock()
    mock_tqdm.return_value = mock_pbar
    
    timer = EventTimer(total_events=2)
    
    # Test milliseconds timing with display update
    timer.record_timing_milliseconds(5000, update_display=True)  # 5 seconds
    
    mock_tqdm.assert_called_once_with(
        total=2,
        desc="Processing",
        unit="events",
        dynamic_ncols=True,
        leave=True,
    )
    mock_pbar.set_postfix.assert_called_once()
    mock_pbar.refresh.assert_called_once()


@patch("steelthread.utils.timing.tqdm")
def test_context_manager_cleanup(mock_tqdm: MagicMock) -> None:
    """Test context manager properly cleans up progress bar."""
    mock_pbar = MagicMock()
    mock_tqdm.return_value = mock_pbar

    with EventTimer(total_events=2) as timer:
        timer.record_timing_seconds(10, update_display=True)

    # Progress bar should be closed
    mock_pbar.close.assert_called_once()


@patch("steelthread.utils.timing.tqdm")
def test_explicit_close(mock_tqdm: MagicMock) -> None:
    """Test explicit close method."""
    mock_pbar = MagicMock()
    mock_tqdm.return_value = mock_pbar

    timer = EventTimer(total_events=2)
    timer.record_timing_seconds(10, update_display=True)

    # Explicitly close
    timer.close()

    mock_pbar.close.assert_called_once()

    # Calling close again should not error
    timer.close()


def test_threading_safety() -> None:
    """Test that timing operations are thread-safe."""
    timer = EventTimer(total_events=10)
    results = []

    def worker() -> None:
        for i in range(5):
            result = timer.record_timing_seconds(0.1 * (i + 1), update_display=False)
            results.append(result)
            time.sleep(0.001)  # Small delay to increase chance of race conditions

    # Start two threads
    thread1 = threading.Thread(target=worker)
    thread2 = threading.Thread(target=worker)

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()

    # Should have recorded 10 events total
    assert timer.processed == 10
    assert len(results) == 10
