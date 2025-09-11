"""Test timing."""

from steelthread.utils.timing import EventTimer


def test_timing() -> None:
    """Test format only."""
    timer = EventTimer(total_events=1)
    timer.record_timing_seconds(120, update_display=False)
    assert timer._pretty(120) == "2m 00s"
