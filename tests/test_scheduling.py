import datetime
import unittest
from unittest.mock import patch

import pytz

import src.scheduling.timeutils as timeutils
from src.customexceptions import TimeZoneError
from src.scheduling.schedule import FixedWindowReportSchedule

FIXED_NOW = datetime.datetime(2000, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)


class WindowScheduleTest(unittest.TestCase):
    def setUp(self):
        self.mock_now = patch("datetime.datetime", wraps=datetime.datetime)
        self.mock_dt = self.mock_now.start()
        self.mock_dt.now.return_value = FIXED_NOW

    def tearDown(self):
        self.mock_now.stop()

    def test_next_occurrence_after_same_time(self):
        t = datetime.time(hour=0, minute=0, second=0)
        dt = datetime.datetime(year=2000, month=1, day=1, hour=0, minute=0, second=0)

        res = timeutils.first_occurrence_after(t, dt)
        xp = datetime.datetime(year=2000, month=1, day=2, hour=0, minute=0, second=0)

        self.assertEqual(res, xp)

    def test_next_occurrence_after_start_before_1(self):
        t = datetime.time(hour=0, minute=0, second=1)
        dt = datetime.datetime(year=2000, month=1, day=1, hour=0, minute=0, second=0)

        res = timeutils.first_occurrence_after(t, dt)
        xp = datetime.datetime(year=2000, month=1, day=1, hour=0, minute=0, second=1)

        self.assertEqual(res, xp)

    def test_next_occurrence_after_start_before_2(self):
        t = datetime.time(hour=1, minute=1, second=1)
        dt = datetime.datetime(year=2000, month=1, day=1, hour=0, minute=0, second=0)

        res = timeutils.first_occurrence_after(t, dt)
        xp = datetime.datetime(year=2000, month=1, day=1, hour=1, minute=1, second=1)

        self.assertEqual(res, xp)

    def test_next_occurrence_after_start_after(self):
        t = datetime.time(hour=0, minute=0, second=0)
        dt = datetime.datetime(year=2000, month=1, day=1, hour=0, minute=0, second=1)

        res = timeutils.first_occurrence_after(t, dt)
        xp = datetime.datetime(year=2000, month=1, day=2, hour=0, minute=0, second=0)

        self.assertEqual(res, xp)

    def test_schedule(self):
        w_s = datetime.time(hour=0, minute=0, second=0)
        w_e = datetime.time(hour=0, minute=0, second=0)
        generation_time = datetime.time(hour=3, minute=0, second=0)

        first = datetime.datetime(year=2000, month=1, day=1, hour=14, minute=0, second=0, tzinfo=datetime.timezone.utc)

        s = FixedWindowReportSchedule(pytz.timezone("UTC"), w_s, w_e, generation_time, first)

        xp_start = datetime.datetime(
            year=2000, month=1, day=1, hour=0, minute=0, second=0, tzinfo=datetime.timezone.utc
        )

        xp_end = datetime.datetime(year=2000, month=1, day=2, hour=0, minute=0, second=0, tzinfo=datetime.timezone.utc)

        xp_gen_time = datetime.datetime(
            year=2000, month=1, day=2, hour=3, minute=0, second=0, tzinfo=datetime.timezone.utc
        )

        start, end = s.next_period()
        gen_time = s.get_next_generation_time()

        self.assertEqual(start, xp_start, "START TIME WRONG!")
        self.assertEqual(end, xp_end, "END TIME WRONG!")
        self.assertEqual(gen_time, xp_gen_time, "GENERATION TIME WRONG!")

        s.advance()
        start, end = s.next_period()
        gen_time = s.get_next_generation_time()

        xp_start += datetime.timedelta(days=1)
        xp_end += datetime.timedelta(days=1)
        xp_gen_time += datetime.timedelta(days=1)

        self.assertEqual(start, xp_start, "START TIME WRONG!")
        self.assertEqual(end, xp_end, "END TIME WRONG!")
        self.assertEqual(gen_time, xp_gen_time, "GENERATION TIME WRONG!")

    def test_bad_timezone(self):
        w_s = w_e = datetime.time(hour=0, minute=0, second=0)
        generation_time = datetime.time(
            hour=3, minute=0, second=0, tzinfo=datetime.timezone(datetime.timedelta(hours=-1), "utc-1")
        )

        first = datetime.datetime(year=2000, month=1, day=1, hour=14, minute=0, second=0)

        with self.assertRaises(TimeZoneError):
            FixedWindowReportSchedule(pytz.timezone("UTC"), w_s, w_e, generation_time, first)

    def test_implicit_utc_no_timezone_times(self):
        w_s = w_e = datetime.time(hour=0, minute=0, second=0)
        generation_time = datetime.time(hour=3, minute=0, second=0)
        first = datetime.datetime(
            year=2000,
            month=1,
            day=1,
            hour=14,
            minute=0,
            second=0,
            tzinfo=datetime.timezone(datetime.timedelta(0), "fake_utc"),
        )

        s = FixedWindowReportSchedule(pytz.timezone("UTC"), w_s, w_e, generation_time, first)

        start, end = s.next_period()
        gen_time = s.get_next_generation_time()

        xp_start = datetime.datetime(
            year=2000,
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            tzinfo=datetime.timezone(datetime.timedelta(0), "fake_utc"),
        )
        xp_end = datetime.datetime(
            year=2000,
            month=1,
            day=2,
            hour=0,
            minute=0,
            second=0,
            tzinfo=datetime.timezone(datetime.timedelta(0), "fake_utc"),
        )
        xp_gen_time = datetime.datetime(
            year=2000,
            month=1,
            day=2,
            hour=3,
            minute=0,
            second=0,
            tzinfo=datetime.timezone(datetime.timedelta(0), "fake_utc"),
        )

        self.assertEqual(start, xp_start, "START TIME WRONG!")
        self.assertEqual(end, xp_end, "END TIME WRONG!")
        self.assertEqual(gen_time, xp_gen_time, "GENERATION TIME WRONG!")

    def test_implicit_utc_timezone_times(self):
        """
        Expect timezones in window and generation times to be ignored.
        """
        w_s = w_e = datetime.time(
            hour=0, minute=0, second=0, tzinfo=datetime.timezone(datetime.timedelta(hours=0), "fake_utc+3")
        )
        generation_time = datetime.time(
            hour=3, minute=0, second=0, tzinfo=datetime.timezone(datetime.timedelta(hours=0), "fake_utc+5")
        )
        first = datetime.datetime(
            year=2000,
            month=1,
            day=1,
            hour=14,
            minute=0,
            second=0,
            tzinfo=datetime.timezone(datetime.timedelta(0), "fake_utc"),
        )

        s = FixedWindowReportSchedule(pytz.timezone("UTC"), w_s, w_e, generation_time, first)

        start, end = s.next_period()
        gen_time = s.get_next_generation_time()

        xp_start = datetime.datetime(
            year=2000, month=1, day=1, hour=0, minute=0, second=0, tzinfo=datetime.timezone.utc
        )
        xp_end = datetime.datetime(year=2000, month=1, day=2, hour=0, minute=0, second=0, tzinfo=datetime.timezone.utc)
        xp_gen_time = datetime.datetime(
            year=2000, month=1, day=2, hour=3, minute=0, second=0, tzinfo=datetime.timezone.utc
        )

        self.assertEqual(start, xp_start, "START TIME WRONG!")
        self.assertEqual(end, xp_end, "END TIME WRONG!")
        self.assertEqual(gen_time, xp_gen_time, "GENERATION TIME WRONG!")

    def test_defaults(self):
        s = FixedWindowReportSchedule(pytz.timezone("UTC"))

        start, end = s.next_period()
        gen_time = s.get_next_generation_time()

        xp_start = datetime.datetime(
            year=2000, month=1, day=1, hour=0, minute=0, second=0, tzinfo=datetime.timezone.utc
        )
        xp_end = datetime.datetime(year=2000, month=1, day=2, hour=0, minute=0, second=0, tzinfo=datetime.timezone.utc)
        xp_gen_time = datetime.datetime(
            year=2000, month=1, day=2, hour=3, minute=0, second=0, tzinfo=datetime.timezone.utc
        )

        self.assertEqual(start, xp_start, "START TIME WRONG!")
        self.assertEqual(end, xp_end, "END TIME WRONG!")
        self.assertEqual(gen_time, xp_gen_time, "GENERATION TIME WRONG!")


if __name__ == "__main__":
    unittest.main()
