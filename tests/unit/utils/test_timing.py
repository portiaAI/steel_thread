"""Test timing."""

import threading
from unittest.mock import MagicMock, patch

from steelthread.utils.timing import EventTimer


def test_timing() -> None:
    """Test format only."""
    timer = EventTimer(total_events=1)
    timer.record_timing_seconds(120, update_display=False)
    assert timer._pretty(120) == "2m 00s"


def test_pretty_formatting() -> None:
    """Test _pretty method with various durations."""
    assert EventTimer._pretty(30) == "30s"
    assert EventTimer._pretty(60) == "1m 00s"
    assert EventTimer._pretty(90) == "1m 30s"
    assert EventTimer._pretty(3665) == "61m 05s"


def test_record_timing_seconds() -> None:
    """Test recording timing in seconds."""
    timer = EventTimer(total_events=3)

    # Record first timing
    avg = timer.record_timing_seconds(10.5, update_display=False)
    assert avg == 10.5
    assert timer.processed == 1
    assert timer.remaining == 2

    # Record second timing
    avg = timer.record_timing_seconds(9.5, update_display=False)
    assert avg == 10.0  # (10.5 + 9.5) / 2
    assert timer.processed == 2
    assert timer.remaining == 1


def test_record_timing_milliseconds() -> None:
    """Test recording timing in milliseconds."""
    timer = EventTimer(total_events=2)

    avg = timer.record_timing_milliseconds(1500, update_display=False)  # 1.5 seconds
    assert avg == 1.5
    assert timer.processed == 1


def test_predict_end() -> None:
    """Test prediction calculations."""
    timer = EventTimer(total_events=4)
    timer.record_timing_seconds(2.0, update_display=False)
    timer.record_timing_seconds(3.0, update_display=False)

    prediction = timer.predict_end()

    # Average is 2.5 seconds, remaining events is 2
    expected_remaining_seconds = 2 * 2.5
    assert prediction["remaining_seconds"] == expected_remaining_seconds
    assert prediction["remaining_pretty"] == "5s"
    assert "eta" in prediction


@patch("steelthread.utils.timing.tqdm")
def test_update_display_initializes_pbar(mock_tqdm_class: MagicMock) -> None:
    """Test that update_display initializes the progress bar on first call."""
    mock_pbar = MagicMock()
    mock_tqdm_class.return_value = mock_pbar

    timer = EventTimer(total_events=5)
    timer.record_timing_seconds(1.0, update_display=False)

    # First call should initialize the progress bar
    timer.update_display()

    expected_bar_format = (
        "{desc}: {percentage:3.0f}%|{bar}| {n}/{total} "
        "[{elapsed}<{remaining}, {rate_fmt}]"
    )
    mock_tqdm_class.assert_called_once_with(
        total=5,
        desc="Processing",
        unit="events",
        bar_format=expected_bar_format,
    )
    mock_pbar.set_description.assert_called_once()
    mock_pbar.refresh.assert_called_once()


@patch("steelthread.utils.timing.tqdm")
def test_update_display_updates_existing_pbar(mock_tqdm_class: MagicMock) -> None:
    """Test that update_display updates existing progress bar on subsequent calls."""
    mock_pbar = MagicMock()
    mock_tqdm_class.return_value = mock_pbar

    timer = EventTimer(total_events=3)
    timer.record_timing_seconds(2.0, update_display=False)

    # First call initializes
    timer.update_display()
    mock_tqdm_class.assert_called_once()

    # Reset mock to check second call
    mock_pbar.reset_mock()
    timer.record_timing_seconds(3.0, update_display=False)

    # Second call should not reinitialize
    timer.update_display()
    mock_tqdm_class.assert_called_once()  # Still only called once from first call
    mock_pbar.set_description.assert_called()
    mock_pbar.refresh.assert_called()

    # Check that progress is updated correctly
    assert mock_pbar.n == 2  # Two events processed


@patch("steelthread.utils.timing.tqdm")
def test_update_display_description_content(mock_tqdm_class: MagicMock) -> None:
    """Test that update_display sets correct description content."""
    mock_pbar = MagicMock()
    mock_tqdm_class.return_value = mock_pbar

    timer = EventTimer(total_events=2)
    timer.record_timing_seconds(1.5, update_display=False)

    timer.update_display()

    # Check that description contains expected information
    call_args = mock_pbar.set_description.call_args[0][0]
    assert "avg=1.50s" in call_args
    assert "left=" in call_args
    assert "ETA=" in call_args


def test_record_timing_with_update_display() -> None:
    """Test that record_timing calls update_display when requested."""
    timer = EventTimer(total_events=2)

    with patch.object(timer, "update_display") as mock_update:
        timer.record_timing_seconds(1.0, update_display=True)
        mock_update.assert_called_once()

        timer.record_timing_seconds(2.0, update_display=False)
        mock_update.assert_called_once()  # Still only once


def test_record_timing_milliseconds_with_update_display() -> None:
    """Test that record_timing_milliseconds calls update_display when requested."""
    timer = EventTimer(total_events=2)

    with patch.object(timer, "update_display") as mock_update:
        timer.record_timing_milliseconds(1500.0, update_display=True)
        mock_update.assert_called_once()

        timer.record_timing_milliseconds(2500.0, update_display=False)
        mock_update.assert_called_once()  # Still only once


def test_close_display() -> None:
    """Test closing the progress bar."""
    timer = EventTimer(total_events=1)

    with patch("steelthread.utils.timing.tqdm") as mock_tqdm_class:
        mock_pbar = MagicMock()
        mock_tqdm_class.return_value = mock_pbar

        # Initialize the progress bar
        timer.update_display()
        assert timer._pbar is not None

        # Close it
        timer.close_display()
        mock_pbar.close.assert_called_once()
        assert timer._pbar is None


def test_close_display_when_no_pbar() -> None:
    """Test closing display when no progress bar exists."""
    timer = EventTimer(total_events=1)

    # Should not raise an error
    timer.close_display()
    assert timer._pbar is None


def test_threading_safety() -> None:
    """Test that the timing operations are thread-safe."""
    timer = EventTimer(total_events=100)
    results = []

    def worker(duration: float) -> None:
        """Worker function for threading test."""
        avg = timer.record_timing_seconds(duration, update_display=False)
        results.append(avg)

    # Start multiple threads
    threads = []
    for i in range(10):
        t = threading.Thread(target=worker, args=(i * 0.1,))
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # Check that all threads recorded their timings
    assert len(results) == 10
    assert timer.processed == 10
