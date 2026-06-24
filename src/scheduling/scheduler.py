import asyncio
import datetime
from dataclasses import dataclass

from loguru import logger

from src.customexceptions import PermanentError, TransientError
from src.generators.ReportGenerator import ReportGenerator
from src.reports.reports import Report
from src.scheduling.schedule import ReportSchedule
from src.scheduling.timeutils import format_timerange, to_utc


@dataclass
class PendingWindow:
    """Dataclass for storing window state closures."""

    start: datetime.datetime
    end: datetime.datetime
    per_ns: bool


class ReportScheduler:
    """
    Schedules generation jobs given a Schedule and ReportGenerator.
    For each ReportGenerator keeps track of uncompleted windows.
    """

    def __init__(
        self,
        schedule: ReportSchedule,
        generators: list[ReportGenerator],
        clock=datetime.datetime.now,
        sleep=asyncio.sleep,
    ) -> None:
        self.schedule: ReportSchedule = schedule
        self.clock = clock
        self.sleep = sleep

        self.pending_windows = {generator: [] for generator in generators}

    async def start(self, per_ns: bool) -> list[Report]:
        """
        > Sleeps until generation time.
        > Extends pending window list.
        > Generates reports.
        > Returns reports
        """
        next_generation_time = self.schedule.get_next_generation_time()
        sleep_time = max(0, (next_generation_time - to_utc(self.clock())).total_seconds())

        for windows in self.pending_windows.values():
            windows.append(PendingWindow(*self.schedule.next_period(), per_ns))

        if sleep_time > 0:
            logger.info(f"Generating next report batch at {next_generation_time.isoformat()}.")
            logger.debug(f"Generating next report batch in {sleep_time} seconds.")

            await self.sleep(sleep_time)

        logger.debug("Generating report batch now.")

        coroutines = []
        for generator, windows in self.pending_windows.items():
            coroutines.append(self.generate_reports(generator, windows))

        results = []
        for result in await asyncio.gather(*coroutines):
            results.extend(result)

        self.schedule.advance()

        return results

    async def generate_reports(self, generator: ReportGenerator, windows: list[PendingWindow]) -> list[Report]:
        """
        > Calls generators to generate reports.
        > Removes window from pending list on success.
        > Returns a list containing all reports that were succsefully generated.
        > Continues on transient errors, raises on permanent ones.
        """
        results = []

        i = 0
        while i < len(windows):
            w = windows[i]
            db_start = w.start
            db_end = w.end

            logger.debug(f"{type(generator).__name__} generating. Time Range:{format_timerange(db_start, db_end)}")
            db_start, db_end = self.schedule.next_period()
            try:
                if w.per_ns:
                    result = await generator.generate_reports(db_start, db_end)
                else:
                    result = await generator.generate_report(db_start, db_end)

            except TransientError:
                i += 1
                continue
            except PermanentError:
                raise

            for report in result:
                logger.info(f"Successfully generated report: {report.filename}.")

            results.extend(result)

            windows.pop(i)

        return results
