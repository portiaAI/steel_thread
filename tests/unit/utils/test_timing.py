"""Test timing."""

from unittest.mock import MagicMock, patch

from steelthread.utils.timing import EventTimer


def test_timing() -> None:
    """Test format only."""
    timer = EventTimer(total_events=1)
    timer.record_timing_seconds(120, update_display=False)
    assert timer._pretty(120) == "2m 00s"


def test_event_timer_basic_functionality() -> None:
    """Test basic EventTimer functionality."""
    timer = EventTimer(total_events=5)

    # Test initial state
    assert timer.processed == 0
    assert timer.remaining == 5
    assert timer.avg_seconds == 0.0

    # Test recording timing
    avg = timer.record_timing_seconds(1.5, update_display=False)
    assert timer.processed == 1
    assert timer.remaining == 4
    assert avg == 1.5

    # Test recording more timings
    timer.record_timing_seconds(2.0, update_display=False)
    timer.record_timing_seconds(1.0, update_display=False)
    assert timer.processed == 3
    assert timer.remaining == 2
    assert timer.avg_seconds == 1.5  # (1.5 + 2.0 + 1.0) / 3


def test_record_timing_milliseconds() -> None:
    """Test recording timing in milliseconds."""
    timer = EventTimer(total_events=2)

    avg = timer.record_timing_milliseconds(1500, update_display=False)
    assert timer.processed == 1
    assert avg == 1.5  # 1500ms = 1.5s


def test_predict_end() -> None:
    """Test prediction functionality."""
    timer = EventTimer(total_events=3)

    # Add some timing data
    timer.record_timing_seconds(2.0, update_display=False)
    timer.record_timing_seconds(3.0, update_display=False)

    prediction = timer.predict_end()

    assert "remaining_seconds" in prediction
    assert "remaining_pretty" in prediction
    assert "eta" in prediction

    # Should predict 1 remaining event * 2.5s average = 2.5s
    assert prediction["remaining_seconds"] == 2.5
    assert prediction["remaining_pretty"] == "2s"  # rounded (2.5 rounds to 2)


def test_pretty_time_formatting() -> None:
    """Test pretty time formatting."""
    assert EventTimer._pretty(30) == "30s"
    assert EventTimer._pretty(60) == "1m 00s"
    assert EventTimer._pretty(90) == "1m 30s"
    assert EventTimer._pretty(3661) == "61m 01s"


@patch("tqdm.tqdm")
def test_update_display_with_tqdm(mock_tqdm_class: MagicMock) -> None:
    """Test update_display method with tqdm integration."""
    # Setup mock tqdm instance
    mock_tqdm_instance = mock_tqdm_class.return_value

    timer = EventTimer(total_events=5)

    # Add some timing data
    timer.record_timing_seconds(1.0, update_display=False)
    timer.record_timing_seconds(2.0, update_display=False)

    # Call update_display which should initialize and update tqdm
    timer.update_display()

    # Verify tqdm was initialized correctly
    mock_tqdm_class.assert_called_once_with(
        total=5,
        desc="Processing",
        unit="events",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
    )

    # Verify tqdm instance was updated correctly
    assert mock_tqdm_instance.n == 2  # 2 processed events
    mock_tqdm_instance.set_postfix.assert_called_once()
    mock_tqdm_instance.refresh.assert_called_once()

    # Verify postfix contains expected keys
    call_args = mock_tqdm_instance.set_postfix.call_args[0][0]
    assert "avg" in call_args
    assert "left" in call_args
    assert "ETA" in call_args


@patch("tqdm.tqdm")
def test_record_timing_with_display_update(mock_tqdm_class: MagicMock) -> None:
    """Test record_timing methods when update_display is True."""
    mock_tqdm_instance = mock_tqdm_class.return_value

    timer = EventTimer(total_events=3)

    # Record timing with display update
    timer.record_timing_seconds(1.5, update_display=True)

    # Verify tqdm was initialized and updated
    mock_tqdm_class.assert_called_once()
    assert mock_tqdm_instance.n == 1
    mock_tqdm_instance.set_postfix.assert_called_once()
    mock_tqdm_instance.refresh.assert_called_once()


@patch("tqdm.tqdm")
def test_progress_bar_initialization_only_once(mock_tqdm_class: MagicMock) -> None:
    """Test that progress bar is only initialized once."""
    timer = EventTimer(total_events=3)

    # Call update_display multiple times
    timer.update_display()
    timer.update_display()
    timer.update_display()

    # tqdm should only be initialized once
    mock_tqdm_class.assert_called_once()


@patch("tqdm.tqdm")
def test_close_progress_bar(mock_tqdm_class: MagicMock) -> None:
    """Test closing the progress bar."""
    mock_tqdm_instance = mock_tqdm_class.return_value

    timer = EventTimer(total_events=2)

    # Initialize progress bar
    timer.update_display()

    # Close progress bar
    timer.close()

    # Verify close was called and progress bar reset
    mock_tqdm_instance.close.assert_called_once()
    assert timer._progress_bar is None

    # Calling close again should not cause issues
    timer.close()  # Should not raise an error


def test_threading_safety() -> None:
    """Test that EventTimer is thread-safe."""
    timer = EventTimer(total_events=100)

    # This test mainly ensures the lock is present and working
    # We can't easily test actual threading here, but the lock should prevent issues
    for i in range(10):
        timer.record_timing_seconds(0.1 * i, update_display=False)

    assert timer.processed == 10
    assert timer.remaining == 90
