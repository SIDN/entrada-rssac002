import datetime
from abc import ABC, abstractmethod

import pytz

from src.scheduling.timeutils import (
    UTC_3AM,
    UTC_MIDNIGHT,
    first_occurrence_after,
    last_occurrence_before,
    to_utc,
    validate_utc,
)


class ReportSchedule(ABC):
    """
    Abstract base class for ReportSchedule
    """

    @abstractmethod
    def get_next_generation_time(self):
        pass

    @abstractmethod
    def next_period(self):
        pass

    @abstractmethod
    def advance(self):
        pass


class FixedWindowReportSchedule(ReportSchedule):
    def __init__(
        self, db_timezone: pytz.BaseTzInfo, window_start=None, window_end=None, generation_time=None, start_time=None
    ) -> None:
        """
        > Given a start_time, this object starts generating reports in windows,
          starting at the first window after (not including) the start_time.

        Converts window start and end times to config-specified database timezone.
        """
        # Parser defaults to None, this is why defaults are handled like this.
        if start_time is None:
            start_time = to_utc(datetime.datetime.now())
        if window_start is None:
            window_start = UTC_MIDNIGHT
        if window_end is None:
            window_end = UTC_MIDNIGHT
        if generation_time is None:
            generation_time = UTC_3AM

        window_start = validate_utc(window_start, "window_start")
        window_end = validate_utc(window_end, "window_end")
        generation_time = validate_utc(generation_time, "generation_time")
        start_time = validate_utc(start_time, "start_time")

        self.db_timezone = db_timezone

        self.last_start = None
        self.last_end = None

        self.next_generation_time = first_occurrence_after(generation_time, start_time)

        self.next_window_end = last_occurrence_before(window_end, self.next_generation_time)
        self.next_window_start = last_occurrence_before(window_start, self.next_window_end)

    def next_period(self) -> tuple[datetime.datetime, datetime.datetime]:
        """Returns window boundaries, both in the database timezone"""
        return (
            self.next_window_start.astimezone(self.db_timezone),
            self.next_window_end.astimezone(self.db_timezone),
        )

    def get_next_generation_time(self):
        """Returns next generation time converted to system timezone"""
        return self.next_generation_time

    def advance(self):
        """
        Advance the window by one day. Update last window.
        """
        self.last_start = self.next_window_start
        self.last_end = self.next_window_end

        self.next_generation_time += datetime.timedelta(days=1)
        self.next_window_start += datetime.timedelta(days=1)
        self.next_window_end += datetime.timedelta(days=1)