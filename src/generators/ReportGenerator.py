from abc import ABC, abstractmethod
from datetime import datetime

from src.querying.query_executors import QueryExecutor
from src.reports.reports import Report
from src.scheduling.timeutils import to_utc


class ReportGenerator(ABC):
    """
    Abstract Base Class for all generator classes.
    Provides an abstract blueprint for its subclasses.
    Also provides some useful shared methods for its subclasses.
    """

    def __init__(self, service_name: str, short_service: str, query_executor: QueryExecutor) -> None:
        """
        service_name: name of tld, parameter for RSSAC002 reports.
        short_service: name to be displayed in filename of report.
        query_executor: QueryExecutor object which provides an interface to execute queries.
        """
        self.service_name = service_name
        self.short_service = short_service
        self.query_executor = query_executor  

    def generate_metadata(self, start_period: datetime) -> dict[str, str | int | datetime]:
        """
        Generates metadata common to all report types.
        """
        return {
            "version": "rssac002v5",
            "service": self.service_name,
            "short_service": self.short_service,
            "start_period": to_utc(start_period),
        }

    def _generate_ns_metadata(self, server: str, start_period: datetime) -> dict:
        """
        Generates nameserver metadata common to all report types.
        This method exists to append the server name to the (short)-service fields.
        """
        ns_short_service = f"{self.short_service}-{server}"
        ns_service = f"{self.service_name}-{server}"

        # Keys with underscores because they will be passed as kwargs:
        return {
            "short_service": ns_short_service,
            "version": "rssac002v5",
            "service": ns_service,
            "start_period": to_utc(start_period),
        }

    # Abstract templates:
    @abstractmethod
    async def generate_report(self, start_period: datetime, end_period: datetime) -> Report:
        pass

    @abstractmethod
    async def generate_reports(self, start_period: datetime, end_period: datetime) -> list[Report]:
        pass

    @abstractmethod
    async def generate_per_ns(self, start_period: datetime, end_period: datetime) -> list[Report]:
        pass
