import asyncio
from copy import deepcopy
from datetime import datetime, time, timedelta, timezone

from tzlocal import get_localzone

from src.scheduling.schedule import FixedWindowReportSchedule


class TimeMock:
    # Default set to 0, s.t. it exits when not set.
    stop_count_max = 0
    cur_stop_count = 0

    def __init__(self, max_calls: int, clock_time: datetime) -> None:
        self.call_count = 0
        self.max_calls = max_calls
        self.clock_time = clock_time
        self.stop_event = asyncio.Event()

    def make_time(self):
        """
        Interpret timezone-agnostic datetime as UTC, then convert this to local timezone.
        Lastly, remove timezone info.
        The database is expected to store times in the local timezone. RSSAC002 reports are UTC-based.
        This allows the caller to specify an expected UTC time, which makes assertions easier.
        """
        copied = deepcopy(self)

        copied.clock_time = copied.clock_time.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)

        def clock():
            return copied.clock_time

        async def sleep(seconds):
            copied.clock_time += timedelta(seconds=seconds)  # Time skip to end of sleep
            copied.call_count += 1
            if copied.call_count == copied.max_calls + 1:
                copied.stop_event.set()
                TimeMock.cur_stop_count += 1

            if TimeMock.cur_stop_count == TimeMock.stop_count_max:  # all schedulers done
                raise StopApplication()

            if copied.stop_event.is_set():
                return  # Return without advancing time

        return clock, sleep

    def make_schedule(self) -> FixedWindowReportSchedule:
        """For now, do midnight until midnight at 3AM, starting at a hardcoded time."""
        return FixedWindowReportSchedule(
            db_timezone=get_localzone(),
            window_start=time(hour=0, minute=0, second=0),
            window_end=time(hour=0, minute=0, second=0),
            generation_time=time(hour=3, minute=0, second=0),
            start_time=datetime(year=2000, month=1, day=2, hour=2, minute=59, second=59, tzinfo=timezone.utc),
        )

    @staticmethod
    def set_stop_count(stop_count: int):
        TimeMock.stop_count_max = stop_count
        TimeMock.cur_stop_count = 0


class StopApplication(BaseException):
    """Exception for killing the app."""

    def __init__(self):
        super().__init__()
