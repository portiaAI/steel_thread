"""Test timing."""

from steelthread.utils.timing import EventTimer


def test_timing() -> None:
    """Test format only."""
    timer = EventTimer(total_events=1)
    try:
        timer.record_timing_seconds(120, update_display=False)
        assert timer._pretty(120) == "2m 00s"
    finally:
        timer.close()


def test_timing_with_context_manager() -> None:
    """Test EventTimer with context manager."""
    with EventTimer(total_events=3) as timer:
        # Record some timings
        timer.record_timing_seconds(1.0, update_display=True)
        timer.record_timing_seconds(2.0, update_display=True)
        timer.record_timing_seconds(1.5, update_display=True)
        
        # Check stats
        assert timer.processed == 3
        assert timer.remaining == 0
        assert timer.avg_seconds == 1.5
