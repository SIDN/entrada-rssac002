import asyncio
import datetime
from collections import defaultdict

from loguru import logger

from src.customexceptions import NoDataException
from src.generators.ReportGenerator import ReportGenerator
from src.querying.query_executors import QueryExecutor
from src.reports.reports import TrafficSizesReport
from src.scheduling.timeutils import check_dates


class TrafficSizesGenerator(ReportGenerator):
    def __init__(self, service_name: str, short_service: str, query_executor: QueryExecutor) -> None:

        super().__init__(service_name, short_service, query_executor)

    async def generate_reports(
        self, start_period: datetime.datetime, end_period: datetime.datetime
    ) -> list[TrafficSizesReport]:
        """
        Generates RSSAC002-defined rcode-volume reports from ENTRADA2 data.
        This function aggregates the per-nameserver query results into a TLD-wide report.
        This exists because in practice, a limited amount of rcodes and servers is used,
          which makes it computationally cheaper to do this aggregation
          instead of querying ENTRADA2 for this aggregated data.
        """
        try:
            results = await self.generate_per_ns(start_period, end_period)
        except NoDataException:
            return [TrafficSizesReport(**self.generate_metadata(start_period))]
        results.append(
            TrafficSizesReport(**self.generate_metadata(start_period), **TrafficSizesReport.reduce_reports(results))
        )

        return results

    async def generate_report(
        self, start_period: datetime.datetime, end_period: datetime.datetime
    ) -> TrafficSizesReport:
        """
        Creates queries that are relevant for the report.
        Calls private query method with these queries (use multithreading because of I/O bound)
        Exports report to specified location.
        """
        check_dates(start_period, end_period)

        logger.debug(f"Querying global traffic-sizes for {start_period} to {end_period}.")
        request_rows, response_rows = await asyncio.gather(
            self.query_executor.query_traffic_sizes_global_request((start_period, end_period)),
            self.query_executor.query_traffic_sizes_global_response((start_period, end_period)),
        )

        PROTOCOLS = {17: "udp", 6: "tcp"}

        traffic_sizes = defaultdict(dict)
        for row in request_rows:
            prot, bucket, volume = row.values()
            stat_name = f"{PROTOCOLS[prot]}-request-sizes"
            traffic_sizes[stat_name][bucket] = volume

        for row in response_rows:
            prot, bucket, volume = row.values()
            stat_name = f"{PROTOCOLS[prot]}-response-sizes"
            traffic_sizes[stat_name][bucket] = volume

        return TrafficSizesReport(
            **self.generate_metadata(start_period),
            udp_request_sizes=traffic_sizes.get("udp-request-sizes", {}),
            udp_response_sizes=traffic_sizes.get("udp-response-sizes", {}),
            tcp_request_sizes=traffic_sizes.get("tcp-request-sizes", {}),
            tcp_response_sizes=traffic_sizes.get("tcp-response-sizes", {}),
        )

    async def generate_per_ns(
        self, start_period: datetime.datetime, end_period: datetime.datetime
    ) -> list[TrafficSizesReport]:

        check_dates(start_period, end_period)

        logger.debug(f"Querying per-nameserver rcode-volume for {start_period} to {end_period}.")
        request_sizes_rows, response_sizes_rows = await asyncio.gather(
            self.query_executor.query_traffic_sizes_per_ns_request((start_period, end_period)),
            self.query_executor.query_traffic_sizes_per_ns_response((start_period, end_period)),
        )

        if len(request_sizes_rows) == 0 and len(response_sizes_rows) == 0:
            logger.warning(f"No data ns-data available for traffic-sizes between {start_period} and {end_period}.")
            raise NoDataException("No data available between {start_period} and {end_period}.")

        PROTOCOLS = {17: "udp", 6: "tcp"}

        traffic_sizes = defaultdict(lambda: defaultdict(dict))

        for row in request_sizes_rows:
            server, prot, bucket, volume = row.values()
            stat_name = f"{PROTOCOLS[prot]}-request-sizes"
            traffic_sizes[server][stat_name][bucket] = volume

        for row in response_sizes_rows:
            server, prot, bucket, volume = row.values()
            stat_name = f"{PROTOCOLS[prot]}-response-sizes"
            traffic_sizes[server][stat_name][bucket] = volume

        ns_reports = []
        for server, traffic_sizes_dict in traffic_sizes.items():
            ns_reports.append(
                TrafficSizesReport(
                    **self._generate_ns_metadata(server, start_period),
                    udp_request_sizes=traffic_sizes_dict.get("udp-request-sizes", {}),
                    udp_response_sizes=traffic_sizes_dict.get("udp-response-sizes", {}),
                    tcp_request_sizes=traffic_sizes_dict.get("tcp-request-sizes", {}),
                    tcp_response_sizes=traffic_sizes_dict.get("tcp-response-sizes", {}),
                    is_ns_report=True,
                )
            )

        return ns_reports
