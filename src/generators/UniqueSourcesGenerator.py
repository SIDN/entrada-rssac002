import asyncio
from datetime import datetime

from loguru import logger

from src.customexceptions import NoDataException
from src.generators.ReportGenerator import ReportGenerator
from src.querying.query_executors import QueryExecutor
from src.reports.reports import Report, UniqueSourcesReport
from src.scheduling.timeutils import check_dates


class UniqueSourcesGenerator(ReportGenerator):
    def __init__(self, service_name: str, short_service: str, query_executor: QueryExecutor) -> None:

        super().__init__(service_name, short_service, query_executor)

    async def generate_reports(self, start_period: datetime, end_period: datetime) -> list[UniqueSourcesReport]:
        """
        Generates RSSAC002-defined unique-sources reports from ENTRADA2 data.
        Here, due to the metric's non-additivity,
            we cannot construct a TLD-wide report from the per-ns reports.
        Hence, this returns a list of TLD-wide reports, with per-nameserver reports.
        """

        report, ns_reports = await asyncio.gather(
            self.generate_report(start_period, end_period),
            self.generate_per_ns(start_period, end_period),
            return_exceptions=True,
        )

        if isinstance(ns_reports, NoDataException):
            return [report]
        else:
            return [report, *ns_reports]

    async def generate_report(self, start_period: datetime, end_period: datetime) -> Report:
        """
        Generates TLD-wide, RSSAC002-defined unique-sources report from ENTRADA2 data.
        """

        check_dates(start_period, end_period)

        logger.debug(f"Querying global unique-sources for {start_period} to {end_period}.")
        rows = await self.query_executor.query_unique_sources_global((start_period, end_period))

        return UniqueSourcesReport(**self.generate_metadata(start_period), **rows[0])

    async def generate_per_ns(self, start_period: datetime, end_period: datetime) -> list[Report]:
        """
        Generates a list of RSSAC002-defined unique-sources reports
            grouped per name server from ENTRADA2 data.
        """

        check_dates(start_period, end_period)

        logger.debug(f"Querying per-nameserver unique-sources for {start_period} to {end_period}.")
        rows = await self.query_executor.query_unique_sources_per_ns((start_period, end_period))

        if len(rows) == 0:
            raise NoDataException(f"No data available between {start_period} and {end_period}.")

        ns_reports = []
        for row in rows:
            server = row.pop("server")
            ns_reports.append(
                UniqueSourcesReport(
                    **self._generate_ns_metadata(server, start_period),
                    **row,
                    is_ns_report=True,
                )
            )
        return ns_reports
