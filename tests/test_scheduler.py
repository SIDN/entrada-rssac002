import datetime
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

import pytz
from loguru import logger

from src.scheduling.schedule import FixedWindowReportSchedule
from src.scheduling.scheduler import ReportScheduler
from src.scheduling.timeutils import to_utc


def make_utc(year, month, day, hour=0, minute=0, second=0) -> datetime.datetime:
    return datetime.datetime(year, month, day, hour, minute, second, tzinfo=datetime.timezone.utc)


def mock_generator(name: str) -> MagicMock:
    gen = MagicMock(name=name)
    gen.generate_reports = AsyncMock(return_value=f"{name}-result")
    return gen


class TestFixedWindowReportSchedule(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        logger.remove()
        return await super().asyncSetUp()

    def _make_subscribers(self) -> dict:
        return {
            "rcode-volume": mock_generator("rcode-volume"),
            "traffic-volume": mock_generator("traffic-volume"),
            "traffic-sizes": mock_generator("traffic-sizes"),
            "unique-sources": mock_generator("unique-sources"),
        }

    def _generators(self) -> list[str]:
        return ["rcode-volume", "traffic-volume", "traffic-sizes", "unique-sources"]

    def _make_schedule_in_past(self) -> FixedWindowReportSchedule:
        """
        Creates a FixedWindowReportSchedule whose generation_time is in
        the past, so sleep_time is zero
        """
        return FixedWindowReportSchedule(
            db_timezone=pytz.timezone("UTC"),
            window_start=make_utc(2026, 5, 9, 6, 0, 0),
            window_end=None,
            generation_time=None,
            start_time=make_utc(2026, 5, 9, 6, 0, 0),
        )

    # start tests
    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_sleep(self, mock_sleep):

        frozen_now = make_utc(2026, 5, 9, 6, 0, 0)
        schedule = self._make_schedule_in_past()

        subscribers = self._make_subscribers()
        generators = self._generators()
        for generator in generators:
            mock_sleep.reset_mock()

            subscribers[generator].generate_reports.return_value = [Result(generator)]

            with patch("src.scheduling.scheduler.datetime.datetime", wraps=datetime.datetime) as mock_dt:
                scheduler = ReportScheduler(schedule, subscribers[generator], mock_dt.now, mock_sleep)
                mocked_now = frozen_now.replace(tzinfo=None)

                mock_dt.now.return_value = mocked_now
                expected_gen = schedule.get_next_generation_time()
                expected_sleep = max(0, (expected_gen - to_utc(mocked_now)).total_seconds())

                await scheduler.start(True)

                mock_sleep.assert_awaited_once()
                actual_sleep = mock_sleep.call_args[0][0]

                self.assertAlmostEqual(actual_sleep, expected_sleep, delta=1)

    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_sleep_is_zero(self, mock_sleep):
        # now is after the next_generation_time, so sleep time is zero
        far_future_now = make_utc(2026, 6, 1, 12, 0, 0)
        schedule = self._make_schedule_in_past()

        subscribers = self._make_subscribers()
        generators = self._generators()
        for generator in generators:
            subscribers[generator].generate_reports.return_value = [Result(generator)]
            scheduler = ReportScheduler(schedule, subscribers[generator])

            with patch("src.scheduling.scheduler.datetime.datetime", wraps=datetime.datetime) as mock_dt:
                mock_dt.now.return_value = far_future_now.replace(tzinfo=None)

                await scheduler.start(True)

            mock_sleep.assert_not_called()

    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_advance_after_generation_time(self, _mock_sleep):

        subscribers = self._make_subscribers()
        generators = self._generators()
        for generator in generators:
            mock_schedule = MagicMock(spec=FixedWindowReportSchedule)

            mock_schedule.next_period.return_value = (make_utc(2026, 5, 9, 0, 0, 0), make_utc(2026, 5, 10, 0, 0, 0))
            mock_schedule.get_next_generation_time.return_value = make_utc(2026, 5, 10, 3, 0, 0)

            subscribers[generator].generate_reports.return_value = [Result(generator)]
            scheduler = ReportScheduler(mock_schedule, subscribers[generator])
            await scheduler.start(True)

            mock_schedule.advance.assert_called_once()

            call_order = [c[0] for c in mock_schedule.method_calls]
            gen_time_idx = call_order.index("get_next_generation_time")
            advance_idx = call_order.index("advance")
            self.assertLess(gen_time_idx, advance_idx, "advance() must be called after get_next_generation_time()")

    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_next_period_before_advance(self, _mock_sleep):
        mock_schedule = MagicMock(spec=FixedWindowReportSchedule)
        mock_schedule.next_period.return_value = (make_utc(2026, 5, 9, 0, 0, 0), make_utc(2026, 5, 10, 0, 0, 0))
        mock_schedule.get_next_generation_time.return_value = make_utc(2026, 5, 10, 3, 0, 0)

        subscribers = self._make_subscribers()
        generators = self._generators()

        for generator in generators:
            subscribers[generator].generate_reports.return_value = [Result(generator)]

        scheduler = ReportScheduler(mock_schedule, subscribers.values())
        await scheduler.start(True)

        call_order = [c[0] for c in mock_schedule.method_calls]
        period_idx = call_order.index("next_period")
        advance_idx = call_order.index("advance")
        self.assertLess(period_idx, advance_idx, "next_period() must be called before advance()")

    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_start_returns_results(self, _mock_sleep):
        schedule = self._make_schedule_in_past()
        subscribers = self._make_subscribers()

        subscribers = self._make_subscribers()
        generators = self._generators()
        for generator in generators:
            subscribers[generator].generate_reports.return_value = [Result(generator)]

        scheduler = ReportScheduler(schedule, subscribers.values())

        result = await scheduler.start(True)

        self.assertIsNotNone(result)

        self.assertListEqual([x.filename for x in result], generators)

    # generate reports tests
    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_called_with_correct_time_window(self, _mock_sleep):

        window_start_utc = make_utc(2026, 5, 9, 6, 0, 0)
        window_end_utc = make_utc(2026, 5, 10, 0, 0, 0)

        mock_schedule = MagicMock(spec=FixedWindowReportSchedule)
        mock_schedule.next_period.return_value = (window_start_utc, window_end_utc)
        mock_schedule.get_next_generation_time.return_value = make_utc(2026, 5, 10, 3, 0, 0)

        subscribers = self._make_subscribers()
        generators = self._generators()
        for generator in generators:
            subscribers[generator].generate_reports.return_value = [Result(generator)]

        scheduler = ReportScheduler(mock_schedule, subscribers.values())

        await scheduler.start(True)

        expected_local_start = window_start_utc
        expected_local_end = window_end_utc

        for generator in generators:
            (
                subscribers[generator].generate_reports.assert_awaited_once_with(
                    expected_local_start, expected_local_end
                ),
                f"Generator '{generator}' received wrong time window",
            )

    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_all_generators_are_called(self, _mock_sleep):
        schedule = self._make_schedule_in_past()

        subscribers = self._make_subscribers()
        generators = self._generators()

        for generator in generators:
            subscribers[generator].generate_reports.return_value = [Result(generator)]

        scheduler = ReportScheduler(schedule, subscribers.values())

        await scheduler.start(True)

        for generator in generators:
            self.assertEqual(
                subscribers[generator].generate_reports.await_count,
                1,
                f"Generator '{generator}' was not called exactly once",
            )

    @patch("asyncio.sleep", new_callable=AsyncMock)
    async def test_generator_exceptions_captured(self, _mock_sleep):
        schedule = self._make_schedule_in_past()
        subscribers = self._make_subscribers()

        subscribers = self._make_subscribers()
        subscribers["rcode-volume"].generate_reports.side_effect = RuntimeError("Exception :(")
        scheduler = ReportScheduler(schedule, subscribers.values())

        with self.assertRaises(RuntimeError):
            await scheduler.start(True)


class Result:
    def __init__(self, filename):
        self.filename = filename
