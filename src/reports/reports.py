from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import reduce
from pathlib import Path
from typing import Self

from src.customexceptions import InvalidReportError

from .histogramutils import REQUEST_BUCKETS, RESPONSE_BUCKETS


@dataclass(kw_only=True)
class Report(ABC):

    short_service: str
    version: str
    service: str
    start_period: datetime
    is_ns_report: bool = False

    def set_rssac002_export_location(self) -> None:
        """
        Compute and set the location relative to the base export location
            to which the report should be exported according to RSSAC002.
        """
        # Convert start date to UTC
        start_date: datetime = self.start_period.astimezone(timezone.utc)
        # Set RSSAC002-compliant export location.
        self.export_loc: Path = Path(str(start_date.year)) / str(start_date.month).zfill(2) / self.metric
        if self.is_ns_report:
            self.export_loc = self.export_loc / 'nameservers'

    def set_rssac002_file_name(self) -> None:
        # Convert start date to UTC
        start_date = self.start_period.astimezone(timezone.utc)
        # RSSAC002-compliant filename
        self.filename = (
            f"{self.short_service}"
            f"-{str(start_date.year).zfill(4)}{str(start_date.month).zfill(2)}{str(start_date.day).zfill(2)}"
            f"-{self.metric}"
            f".yaml"
        )

    def __post_init__(self) -> None:
        self.set_rssac002_export_location()
        self.set_rssac002_file_name()

    def to_dict(self) -> dict[str, str | int]:
        return {
            "version": self.version,
            "service": self.service,
            "metric": self.metric,
            "start-period": self.start_period.astimezone(timezone.utc).isoformat(),
        }


def sum_dictionaries(left: dict, right: dict) -> dict:
    """
    Sums two dictionaries.
    Supports key: dict and key: int
    Assumption: for each report, any one key should hold a value of the same data type in both reports.
    """
    result = {}
    for key in left.keys() | right.keys():
        left_val = left.get(key, 0)
        right_val = right.get(key, 0)

        if isinstance(left_val, dict) and isinstance(right_val, dict):
            result[key] = sum_dictionaries(left_val, right_val)
        elif isinstance(left_val, dict):
            result[key] = sum_dictionaries(left_val, {})
        elif isinstance(right_val, dict):
            result[key] = sum_dictionaries({}, right_val)
        else:
            result[key] = left_val + right_val

    return result


@dataclass(kw_only=True)
class TrafficVolumeReport(Report):
    dns_udp_queries_received_ipv4: int = 0
    dns_udp_queries_received_ipv6: int = 0
    dns_tcp_queries_received_ipv4: int = 0
    dns_tcp_queries_received_ipv6: int = 0
    dns_udp_responses_sent_ipv4: int = 0
    dns_udp_responses_sent_ipv6: int = 0
    dns_tcp_responses_sent_ipv4: int = 0
    dns_tcp_responses_sent_ipv6: int = 0

    def __post_init__(self) -> None:
        self.metric = "traffic-volume"
        self.validate()
        super().__post_init__()

    @property
    def fields(self) -> dict[str, int]:
        return {
            "dns-udp-queries-received-ipv4": self.dns_udp_queries_received_ipv4,
            "dns-udp-queries-received-ipv6": self.dns_udp_queries_received_ipv6,
            "dns-tcp-queries-received-ipv4": self.dns_tcp_queries_received_ipv4,
            "dns-tcp-queries-received-ipv6": self.dns_tcp_queries_received_ipv6,
            "dns-udp-responses-sent-ipv4": self.dns_udp_responses_sent_ipv4,
            "dns-udp-responses-sent-ipv6": self.dns_udp_responses_sent_ipv6,
            "dns-tcp-responses-sent-ipv4": self.dns_tcp_responses_sent_ipv4,
            "dns-tcp-responses-sent-ipv6": self.dns_tcp_responses_sent_ipv6,
        }

    def validate(self) -> None:
        for name, value in self.fields.items():
            if not isinstance(value, int):
                raise InvalidReportError(
                    f"Invalid traffic-volume report:"
                    f"expected value ({value}) to be of type int, but is of type: {type(value)}."
                )
            if value < 0:
                raise InvalidReportError(f"Invalid traffic-volume report: negative value ({name}:{value}).")

    def to_dict(self) -> dict[str, str | int]:
        return super().to_dict() | self.fields

    @staticmethod
    def sum_reports(left: dict[str, int], right: Self) -> dict[str, int]:
        return sum_dictionaries(left, right.fields)

    @staticmethod
    def reduce_reports(reports: list[Self]) -> dict[str, int]:
        if len(reports) == 1:
            res = reports[0].fields
        else:
            dummy_report = TrafficVolumeReport(short_service="", version="", service="", start_period=datetime.now())
            res = reduce(TrafficVolumeReport.sum_reports, reports, dummy_report.fields)

        return {key.replace("-", "_"): value for key, value in res.items()}


@dataclass(kw_only=True)
class TrafficSizesReport(Report):
    udp_request_sizes: dict[str, int] = field(default_factory=dict)
    udp_response_sizes: dict[str, int] = field(default_factory=dict)
    tcp_request_sizes: dict[str, int] = field(default_factory=dict)
    tcp_response_sizes: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.metric = "traffic-sizes"
        self.validate()
        super().__post_init__()

    @property
    def fields(self):
        return {
            "udp-request-sizes": self.udp_request_sizes,
            "udp-response-sizes": self.udp_response_sizes,
            "tcp-request-sizes": self.tcp_request_sizes,
            "tcp-response-sizes": self.tcp_response_sizes,
        }

    def validate_hist(self, hist_name: str, hist: dict[str, int], buckets: set[str]) -> dict[str, int]:
        if not isinstance(hist, dict):
            raise InvalidReportError(f"Invalid traffic-sizes report: {hist_name} is not a dictionary.")

        validated_hist = {}
        for key, value in hist.items():
            if key not in buckets:
                raise InvalidReportError(
                    f"Invalid traffic-sizes report: {hist_name} histogram contains unknown key: {key}."
                )
            if not isinstance(value, int):
                raise InvalidReportError(
                    f"Invalid traffic-sizes report: {hist_name} histogram contains a non-integer value: {key}: {value}"
                )
            if value < 0:
                raise InvalidReportError(
                    f"Invalid traffic-sizes report: {hist_name} contains negative value: {key}: {value}."
                )
            if value > 0:
                validated_hist[key] = value

        return validated_hist

    def validate(self) -> None:
        self.udp_request_sizes = self.validate_hist("udp-request-sizes", self.udp_request_sizes, REQUEST_BUCKETS)
        self.udp_response_sizes = self.validate_hist("udp-response-sizes", self.udp_response_sizes, RESPONSE_BUCKETS)
        self.tcp_request_sizes = self.validate_hist("tcp-request-sizes", self.tcp_request_sizes, REQUEST_BUCKETS)
        self.tcp_response_sizes = self.validate_hist("tcp-response-sizes", self.tcp_response_sizes, RESPONSE_BUCKETS)

    def to_dict(self) -> dict[str, str | int | dict[str, int]]:
        return super().to_dict() | self.fields

    @staticmethod
    def sum_reports(left: dict[dict[str, int]], right: Self) -> dict[dict[str, int]]:
        return sum_dictionaries(left, right.fields)

    @staticmethod
    def reduce_reports(reports: list[Self]) -> dict[dict[str, int]]:
        if len(reports) == 1:
            res = reports[0].fields
        else:
            dummy_report = TrafficSizesReport(short_service="", version="", service="", start_period=datetime.now())
            res = reduce(TrafficSizesReport.sum_reports, reports, dummy_report.fields)

        # Replace hyphens with underscores, needed to directly pass to Report object in generator.
        return {key.replace("-", "_"): value for key, value in res.items()}


RCODE_MIN = 0
RCODE_MAX = 4095


@dataclass(kw_only=True)
class RCodeVolumeReport(Report):
    rcode_volume: dict[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.metric = "rcode-volume"
        self.validate()
        super().__post_init__()

    @property
    def fields(self):
        return self.rcode_volume

    def validate(self) -> None:
        if not isinstance(self.rcode_volume, dict):
            raise InvalidReportError("Invalid rcode-volume report: rcode-volume is not a dictionary.")

        validated_rcode_volume = {}
        for rcode, volume in self.rcode_volume.items():
            if not isinstance(rcode, int):
                raise InvalidReportError(f"Invalid rcode-volume report: key {rcode} is not an integer.")
            if not isinstance(volume, int):
                raise InvalidReportError(
                    f"Invalid rcode-volume report: expected value ({volume}) to be int, but got {type(volume)}."
                )

            if rcode < RCODE_MIN or rcode > RCODE_MAX:
                raise InvalidReportError(
                    f"Invalid rcode-volume report:rcode must be between {RCODE_MIN} and {RCODE_MAX}: {rcode}"
                )

            if volume < 0:
                raise InvalidReportError(f"Invalid rcode-volume report: negative RCODE volume ({rcode}: {volume}).")

            if volume > 0:
                validated_rcode_volume[rcode] = volume

        self.rcode_volume = validated_rcode_volume

    def to_dict(self) -> dict[int, int]:
        return super().to_dict() | dict(sorted(self.rcode_volume.items(), key=lambda x: x[0]))

    @staticmethod
    def sum_reports(left: dict[int, int], right: Self) -> dict[int, int]:
        return sum_dictionaries(left, right.fields)

    @staticmethod
    def reduce_reports(reports: list[Self]) -> dict[int, int]:
        if len(reports) == 1:
            res = reports[0].fields
        else:
            dummy_report = RCodeVolumeReport(short_service="", version="", service="", start_period=datetime.now())
            res = reduce(RCodeVolumeReport.sum_reports, reports, dummy_report.fields)

        return res


@dataclass(kw_only=True)
class UniqueSourcesReport(Report):
    """
    Doesn't have an add_reports function, because of the metric's non-additivity.
    """

    num_sources_ipv4: int = 0
    num_sources_ipv6: int = 0
    num_sources_ipv6_aggregate: int = 0

    def __post_init__(self):
        self.metric = "unique-sources"
        self.validate()
        super().__post_init__()

    @property
    def fields(self):
        return {
            "num-sources-ipv4": self.num_sources_ipv4,
            "num-sources-ipv6": self.num_sources_ipv6,
            "num-sources-ipv6-aggregate": self.num_sources_ipv6_aggregate,
        }

    def validate(self):
        for name, value in self.fields.items():
            if not isinstance(value, int):
                raise InvalidReportError(
                    f"Invalid unique-sources report:"
                    f"expected value ({value}) to be of type int, but is of type: {type(value)}."
                )
            if value < 0:
                raise InvalidReportError(f"Invalid unique-sources report: negative value ({name}: {value}).")

    def to_dict(self) -> dict[str, int]:
        return super().to_dict() | {key: value for key, value in self.fields.items() if value > 0}
