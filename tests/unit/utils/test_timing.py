"""Test timing."""

from unittest import mock
from unittest.mock import MagicMock

from steelthread.utils.timing import EventTimer


def test_timing() -> None:
    """Test format only."""
    timer = EventTimer(total_events=1)
    timer.record_timing_seconds(120, update_display=False)
    assert timer._pretty(120) == "2m 00s"


def test_pretty_format_seconds_only() -> None:
    """Test pretty format for seconds only."""
    timer = EventTimer(total_events=1)
    assert timer._pretty(30) == "30s"


def test_pretty_format_minutes_seconds() -> None:
    """Test pretty format for minutes and seconds."""
    timer = EventTimer(total_events=1)
    assert timer._pretty(90) == "1m 30s"
    assert timer._pretty(125) == "2m 05s"


def test_timer_properties() -> None:
    """Test timer properties."""
    timer = EventTimer(total_events=10)
    assert timer.processed == 0
    assert timer.remaining == 10
    assert timer.avg_seconds == 0.0

    timer.record_timing_seconds(5.0, update_display=False)
    assert timer.processed == 1
    assert timer.remaining == 9
    assert timer.avg_seconds == 5.0

    timer.record_timing_seconds(3.0, update_display=False)
    assert timer.processed == 2
    assert timer.remaining == 8
    assert timer.avg_seconds == 4.0


def test_record_timing_milliseconds() -> None:
    """Test recording timing in milliseconds."""
    timer = EventTimer(total_events=5)
    avg = timer.record_timing_milliseconds(2000, update_display=False)
    assert avg == 2.0
    assert timer.avg_seconds == 2.0


@mock.patch("steelthread.utils.timing.tqdm")
def test_record_timing_milliseconds_with_display(mock_tqdm_module: MagicMock) -> None:
    """Test recording timing in milliseconds with display update."""
    mock_progress_bar = mock.Mock()
    mock_progress_bar.n = 0
    mock_tqdm_module.tqdm.return_value = mock_progress_bar

    timer = EventTimer(total_events=5)
    avg = timer.record_timing_milliseconds(3000, update_display=True)
    assert avg == 3.0
    assert timer.avg_seconds == 3.0

    # Check that progress bar was updated
    mock_progress_bar.update.assert_called_once_with(1)
    mock_progress_bar.set_postfix_str.assert_called_once()


def test_predict_end() -> None:
    """Test end prediction."""
    timer = EventTimer(total_events=3)
    timer.record_timing_seconds(2.0, update_display=False)

    prediction = timer.predict_end()
    assert prediction["remaining_seconds"] == 4.0  # 2 remaining * 2.0 avg
    assert prediction["remaining_pretty"] == "4s"
    assert "eta" in prediction


@mock.patch("steelthread.utils.timing.tqdm")
def test_update_display_with_tqdm(mock_tqdm_module: MagicMock) -> None:
    """Test update_display initializes and updates tqdm progress bar."""
    mock_progress_bar = mock.Mock()
    mock_progress_bar.n = 0
    mock_tqdm_module.tqdm.return_value = mock_progress_bar

    timer = EventTimer(total_events=5)
    timer.record_timing_seconds(1.5, update_display=True)

    # Check that tqdm was initialized
    mock_tqdm_module.tqdm.assert_called_once_with(
        total=5,
        desc="Processing",
        unit="events",
    )

    # Check that progress bar was updated
    mock_progress_bar.update.assert_called_once_with(1)
    mock_progress_bar.set_postfix_str.assert_called_once()


@mock.patch("steelthread.utils.timing.tqdm")
def test_update_display_no_update_needed(mock_tqdm_module: MagicMock) -> None:
    """Test update_display when no progress update is needed."""
    mock_progress_bar = mock.Mock()
    mock_tqdm_module.tqdm.return_value = mock_progress_bar
    mock_progress_bar.n = 2

    timer = EventTimer(total_events=5)
    timer.record_timing_seconds(1.0, update_display=False)
    timer.record_timing_seconds(1.0, update_display=False)

    # Manually set progress bar as if it was already initialized
    timer._progress_bar = mock_progress_bar

    timer.update_display()

    # Should not call update since progress hasn't changed (n=2, processed=2)
    mock_progress_bar.update.assert_not_called()
    mock_progress_bar.set_postfix_str.assert_called_once()


def test_close_progress_bar() -> None:
    """Test closing progress bar."""
    with mock.patch("steelthread.utils.timing.tqdm") as mock_tqdm_module:
        mock_progress_bar = mock.Mock()
        mock_progress_bar.n = 0
        mock_tqdm_module.tqdm.return_value = mock_progress_bar

        timer = EventTimer(total_events=5)
        timer.update_display()  # Initialize progress bar

        timer.close()

        mock_progress_bar.close.assert_called_once()
        assert timer._progress_bar is None


def test_close_no_progress_bar() -> None:
    """Test closing when no progress bar exists."""
    timer = EventTimer(total_events=5)
    timer.close()  # Should not raise any exception
    assert timer._progress_bar is None


def test_threading_safety() -> None:
    """Test that timer works with threading lock."""
    timer = EventTimer(total_events=10)

    # This should work without issues due to the lock
    timer.record_timing_seconds(1.0, update_display=False)
    timer.record_timing_milliseconds(2000, update_display=False)

    assert timer.processed == 2
    assert timer.avg_seconds == 1.5


@mock.patch("steelthread.utils.timing.tqdm")
def test_multiple_update_display_calls(mock_tqdm_module: MagicMock) -> None:
    """Test multiple calls to update_display only initialize tqdm once."""
    mock_progress_bar = mock.Mock()
    mock_progress_bar.n = 0
    mock_tqdm_module.tqdm.return_value = mock_progress_bar

    timer = EventTimer(total_events=3)
    timer.record_timing_seconds(1.0, update_display=True)
    timer.record_timing_seconds(1.0, update_display=True)

    # tqdm should only be initialized once
    assert mock_tqdm_module.tqdm.call_count == 1
