"""Timing utils."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tqdm import tqdm


@dataclass
class EventTimer:
    """Simple event timer to predict completion."""

    total_events: int
    times: list[float] = field(default_factory=list)  # seconds per finished event
    _lock = threading.Lock()
    _progress_bar: tqdm | None = field(default=None, init=False)

    def _init_progress_bar(self) -> None:
        """Initialize the progress bar if not already done."""
        if self._progress_bar is None:
            # Import at runtime to avoid issues with optional dependency
            try:
                from tqdm import tqdm  # noqa: PLC0415
            except ImportError as e:
                msg = "tqdm is required for progress bar display. Install with: pip install tqdm"
                raise ImportError(msg) from e

            self._progress_bar = tqdm(
                total=self.total_events,
                desc="Processing",
                unit="events",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
            )

    def record_timing_seconds(self, seconds: float, update_display: bool) -> float:
        """Record one event's duration."""
        with self._lock:
            self.times.append(float(seconds))
            if update_display:
                self.update_display()
            return self.avg_seconds

    def record_timing_milliseconds(self, milliseconds: float, update_display: bool) -> float:
        """Record one event's duration."""
        with self._lock:
            self.times.append(float(milliseconds / 1000))
            if update_display:
                self.update_display()
            return self.avg_seconds

    # --- Stats ---------------------------------------------------------------
    @property
    def processed(self) -> int:
        """Get total number of events."""
        return len(self.times)

    @property
    def remaining(self) -> int:
        """Get remaining events."""
        return max(self.total_events - self.processed, 0)

    @property
    def avg_seconds(self) -> float:
        """Get average duration."""
        return sum(self.times) / len(self.times) if self.times else 0.0

    # --- Predictions ---------------------------------------------------------
    def predict_end(self) -> dict:
        """Predict completion based on the running average.

        Returns a dict with:
        - 'remaining_seconds'
        - 'remaining_pretty' (e.g., '12m 05s')
        - 'eta' (datetime when all events finish)
        """
        rem_seconds = self.remaining * self.avg_seconds
        eta = datetime.now(tz=UTC) + timedelta(seconds=rem_seconds)
        return {
            "remaining_seconds": rem_seconds,
            "remaining_pretty": self._pretty(rem_seconds),
            "eta": eta,
        }

    # --- Display -------------------------------------------------------------
    def update_display(self) -> None:
        """Update progress bar with latest stats."""
        self._init_progress_bar()

        if self._progress_bar is not None:
            predicted = self.predict_end()

            # Update the progress bar position to current processed count
            self._progress_bar.n = self.processed

            # Set the postfix with timing information
            postfix = {
                "avg": f"{self.avg_seconds:.2f}s",
                "left": predicted["remaining_pretty"],
                "ETA": predicted["eta"].strftime("%H:%M:%S")
            }
            self._progress_bar.set_postfix(postfix)
            self._progress_bar.refresh()

    def close(self) -> None:
        """Close the progress bar if it exists."""
        if self._progress_bar is not None:
            self._progress_bar.close()
            self._progress_bar = None

    # --- Helpers -------------------------------------------------------------
    @staticmethod
    def _pretty(seconds: float) -> str:
        seconds = round(seconds)
        m, s = divmod(seconds, 60)
        if m == 0:
            return f"{s}s"
        return f"{m}m {s:02d}s"
