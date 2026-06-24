from datetime import datetime

from loguru import logger

from src.customexceptions import NoDataException
from src.generators.ReportGenerator import ReportGenerator
from src.querying.query_executors import QueryExecutor
from src.reports.reports import TrafficVolumeReport
from src.scheduling.timeutils import check_dates


class TrafficVolumeGenerator(ReportGenerator):
    def __init__(self, service_name: str, short_service: str, query_executor: QueryExecutor) -> None:

        super().__init__(service_name, short_service, query_executor)

    async def generate_reports(self, start_period: datetime, end_period: datetime) -> list[TrafficVolumeReport]:
        """
        Generates RSSAC002-defined traffic-volume reports from ENTRADA2 data.
        This function aggregates the per-nameserver query results into a TLD-wide report.
        This exists because in practice, a limited set of nameservers is used,
          which makes it coputationally cheaper to do this aggregation
          instead of querying ENTRADA2 for this aggregated data.
        """

        try:
            results = await self.generate_per_ns(start_period, end_period)
        except NoDataException:
            return [TrafficVolumeReport(**self.generate_metadata(start_period))]

        results.append(
            TrafficVolumeReport(**self.generate_metadata(start_period), **TrafficVolumeReport.reduce_reports(results))
        )

        return results

    async def generate_report(self, start_period: datetime, end_period: datetime) -> TrafficVolumeReport:
        """
        Creates queries that are relevant for the report.
        Calls private query method with these queries (use multithreading because of I/O bound)
        Exports report to specified location.
        """

        check_dates(start_period, end_period)

        logger.debug(f"Querying global traffic-volume for {start_period} to {end_period}.")
        results = await self.query_executor.query_traffic_volume_global((start_period, end_period))

        return TrafficVolumeReport(**self.generate_metadata(start_period), **results[0])

    async def generate_per_ns(self, start_period: datetime, end_period: datetime) -> list[TrafficVolumeReport]:

        check_dates(start_period, end_period)

        logger.debug(f"Querying per-nameserver traffic-volume for {start_period} to {end_period}.")
        rows = await self.query_executor.query_traffic_volume_per_ns((start_period, end_period))

        if len(rows) == 0:
            logger.warning(f"No ns-data available for traffic-volume between {start_period} and {end_period}.")
            raise NoDataException(f"No data observed between {start_period} and {end_period}.")

        ns_reports = []
        for row in rows:
            server = row.pop("server")
            ns_reports.append(
                TrafficVolumeReport(
                    **self._generate_ns_metadata(server, start_period),
                    **row,
                    is_ns_report=True,
                )
            )

        return ns_reports
