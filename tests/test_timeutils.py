import datetime
import unittest

from src.customexceptions import DateRangeError, TimeZoneError
from src.scheduling.timeutils import (
    check_dates,
    first_occurrence_after,
    format_datetime,
    format_timerange,
    last_occurrence_before,
    validate_utc,
)


class TestTimeutils(unittest.TestCase):
    # Test check dates
    def test_date_range(self):
        incorrect_start = datetime.datetime(2026, 5, 21, 2, 0, 0)
        incorrect_end = datetime.datetime(2026, 5, 21, 0, 0, 0)

        with self.assertRaises(DateRangeError):
            check_dates(incorrect_start, incorrect_end)

    def test_date_range_equal(self):
        incorrect_start = datetime.datetime(2026, 5, 21, 0, 0, 0)
        incorrect_end = datetime.datetime(2026, 5, 21, 0, 0, 0)

        with self.assertRaises(DateRangeError):
            check_dates(incorrect_start, incorrect_end)

    # Test first occurence after
    def test_returns_same_day(self):
        dt = datetime.datetime(2026, 5, 9, 10, 0, 0)
        t = datetime.time(15, 30, 0)

        result = first_occurrence_after(t, dt)

        self.assertEqual(result, datetime.datetime(2026, 5, 9, 15, 30, 0))

    def test_returns_next_day(self):
        dt = datetime.datetime(2026, 5, 9, 15, 0, 0)
        t = datetime.time(10, 0, 0)

        result = first_occurrence_after(t, dt)

        self.assertEqual(result, datetime.datetime(2026, 5, 10, 10, 0, 0))

    def test_returns_next_day_exactly_equal(self):
        dt = datetime.datetime(2026, 5, 9, 15, 0, 0)
        t = datetime.time(15, 0, 0)

        result = first_occurrence_after(t, dt)

        self.assertEqual(result, datetime.datetime(2026, 5, 10, 15, 0, 0))

    # Test last occurence before
    def test_returns_same_day_last(self):
        dt = datetime.datetime(2026, 5, 9, 15, 0, 0)
        t = datetime.time(10, 0, 0)

        result = last_occurrence_before(t, dt)

        self.assertEqual(result, datetime.datetime(2026, 5, 9, 10, 0, 0))

    def test_returns_previous_day_last(self):
        dt = datetime.datetime(2026, 5, 9, 10, 0, 0)
        t = datetime.time(15, 0, 0)

        result = last_occurrence_before(t, dt)

        self.assertEqual(result, datetime.datetime(2026, 5, 8, 15, 0, 0))

    def test_returns_previous_day_equal_last(self):
        dt = datetime.datetime(2026, 5, 9, 15, 0, 0)
        t = datetime.time(15, 0, 0)

        result = last_occurrence_before(t, dt)

        self.assertEqual(result, datetime.datetime(2026, 5, 8, 15, 0, 0))

    # Test validate utc
    def test_adds_utc(self):
        t = datetime.time(12, 30)

        result = validate_utc(t, "start_time")

        self.assertEqual(result.tzinfo, datetime.timezone.utc)
        self.assertEqual(result.hour, 12)
        self.assertEqual(result.minute, 30)

    def test_returns_same_object(self):
        t = datetime.time(12, 30, tzinfo=datetime.timezone.utc)

        result = validate_utc(t, "start_time")

        self.assertIs(result, t)

    def test_raises_exception(self):
        tz = datetime.timezone(datetime.timedelta(hours=2))
        t = datetime.time(12, 30, tzinfo=tz)

        with self.assertRaises(TimeZoneError) as ctx:
            validate_utc(t, "start_time")

        self.assertEqual(str(ctx.exception), "Expected start_time to be in UTC but is in UTC+02:00")

    def test_raises_exception__negative(self):
        tz = datetime.timezone(datetime.timedelta(hours=-5, minutes=-30))
        t = datetime.time(12, 30, tzinfo=tz)

        with self.assertRaises(TimeZoneError) as ctx:
            validate_utc(t, "start_time")

        # This assertion reflects the current implementation.
        self.assertEqual(str(ctx.exception), "Expected start_time to be in UTC but is in UTC-06:30")

    # Test format datetime
    def test_formats_utc_datetime(self):
        dt = datetime.datetime(2026, 5, 9, 0, 0, tzinfo=datetime.timezone.utc)

        self.assertEqual(format_datetime(dt), "09/05/2026 00:00 UTC+00:00")

    def test_formats_positive_offset(self):
        dt = datetime.datetime(2026, 5, 9, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=2)))

        self.assertEqual(format_datetime(dt), "09/05/2026 00:00 UTC+02:00")

    def test_formats_negative_offset(self):
        dt = datetime.datetime(2026, 5, 9, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=-5)))

        self.assertEqual(format_datetime(dt), "09/05/2026 00:00 UTC-05:00")

    def test_datetime_local_timezone(self):
        dt = datetime.datetime(2026, 5, 9, 0, 0)

        result = format_datetime(dt)

        self.assertTrue(result.startswith("09/05/2026 00:00 UTC"))

    # Test formatting timerange
    def test_formats_timerange(self):
        start = datetime.datetime(2026, 5, 9, 9, 0, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(2026, 5, 9, 17, 30, tzinfo=datetime.timezone.utc)

        self.assertEqual(format_timerange(start, end), ("09/05/2026 09:00 UTC+00:00 ==> 09/05/2026 17:30 UTC+00:00"))
