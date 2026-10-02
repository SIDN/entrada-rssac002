from datetime import datetime

from loguru import logger

from src.customexceptions import NoDataException
from src.generators.ReportGenerator import ReportGenerator
from src.querying.query_executors import QueryExecutor
from src.reports.reports import RCodeVolumeReport
from src.scheduling.timeutils import check_dates


class RCodeVolumeGenerator(ReportGenerator):
    def __init__(self, service_name: str, short_service: str, query_executor: QueryExecutor) -> None:

        super().__init__(service_name, short_service, query_executor)

    async def generate_reports(self, start_period: datetime, end_period: datetime) -> list[RCodeVolumeReport]:
        """
        > Generates RSSAC002-defined rcode-volume reports from ENTRADA2 data.
        > Aggregates the per-nameserver query results into a TLD-wide report.
        > This exists because in practice, a limited amount of rcodes and servers is used,
          which makes it computationally cheaper to do this aggregation
          instead of querying ENTRADA2 for this aggregated data.
        """
        try:
            results = await self.generate_per_ns(start_period, end_period)
        except NoDataException:
            return [RCodeVolumeReport(**self.generate_metadata(start_period))]

        results.append(
            RCodeVolumeReport(
                **self.generate_metadata(start_period), rcode_volume=RCodeVolumeReport.reduce_reports(results)
            )
        )

        return results

    async def generate_report(self, start_period: datetime, end_period: datetime) -> RCodeVolumeReport:
        """
        > Generates TLD-wide, RSSAC002-defined rcode-volume report from ENTRADA2 data.
        > Expects start_period and end_period to be in the database timezone.
        """
        check_dates(start_period, end_period)

        logger.debug(f"Querying global rcode-volume for {start_period} to {end_period}.")
        rows = await self.query_executor.query_rcode_volume_global((start_period, end_period))

        rcodes = {}
        for row in rows:
            rcode, volume = row.values()
            rcodes[rcode] = volume

        return RCodeVolumeReport(**self.generate_metadata(start_period), rcode_volume=rcodes)

    async def generate_per_ns(self, start_period: datetime, end_period: datetime) -> list[RCodeVolumeReport]:
        """
        Generates a list of RSSAC002-defined rcode-volume reports grouped per name server from ENTRADA2 data.
        """
        check_dates(start_period, end_period)

        logger.debug(f"Querying per-nameserver rcode-volume for {start_period} to {end_period}.")
        rows = await self.query_executor.query_rcode_volume_per_ns((start_period, end_period))

        if len(rows) == 0:
            logger.warning(f"No ns-data available for rcode-volume between {start_period} and {end_period}.")
            raise NoDataException(f"No data available between {start_period} and {end_period}.")

        rcodes = {}
        for row in rows:
            server, rcode, volume = row.values()
            rcodes[server] = rcodes.get(server, {}) | {rcode: volume}

        ns_reports = []
        for server, rcode_dict in rcodes.items():
            normalized = {
                (-1 if rcode is None else rcode): count
                for rcode, count in rcode_dict.items()
            }
            ns_reports.append(
                RCodeVolumeReport(
                    **self._generate_ns_metadata(server, start_period),
                    rcode_volume=dict(sorted(normalized.items(), key=lambda x: x[0])),
                    is_ns_report=True,
                )
            )

        return ns_reports
