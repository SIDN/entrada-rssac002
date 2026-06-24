import datetime
from pathlib import Path
from typing import Literal

import pytz
import yaml
from pydantic import BaseModel, Field

from src.generators.RCodeVolumeGenerator import RCodeVolumeGenerator
from src.generators.TrafficSizesGenerator import TrafficSizesGenerator
from src.generators.TrafficVolumeGenerator import TrafficVolumeGenerator
from src.generators.UniqueSourcesGenerator import UniqueSourcesGenerator
from src.querying.query_executors import QueryExecutor, TrinoQueryExecutor
from src.scheduling.schedule import FixedWindowReportSchedule, ReportSchedule
from src.scheduling.scheduler import ReportScheduler


class FixedWindowScheduleConfig(BaseModel):
    type: Literal["fixed_window"]
    window_start: datetime.time | None = None
    window_end: datetime.time | None = None
    generation_time: datetime.time | None = None
    start_time: datetime.datetime | None = None

    def convert_utc(self, t: None | datetime.datetime) -> None | datetime.time | datetime.datetime:
        """Convert datetime/time to utc, return None if None."""
        if t is None:
            return t
        elif t.tzinfo is None:
            return t.replace(tzinfo=datetime.timezone.utc)
        else: 
            return t

    def build(self, db_timezone: pytz.BaseTzInfo) -> ReportSchedule:
        """Instantiates FixedWindowReportSchedule with UTC times."""
        return FixedWindowReportSchedule(
            db_timezone,
            self.window_start,
            self.window_end,
            self.generation_time,
            self.convert_utc(self.start_time),
        )


class QueryExecutorConfig(BaseModel):
    engine: Literal["trino"]
    host: str
    port: int
    user: str
    catalog: str
    schema_: str = Field(alias="schema")

    def build(self) -> QueryExecutor:
        executor_classes = {"trino": TrinoQueryExecutor(self.host, self.port, self.user, self.catalog, self.schema_)}

        return executor_classes[self.engine]


class Config(BaseModel):
    export_root: str
    db_timezone: str
    service_name: str
    short_service: str
    per_ns_mode: bool
    schedule: FixedWindowScheduleConfig
    query_executor: QueryExecutorConfig = Field(alias="query_connection")


def parse_timezone(tz_string: str) -> pytz.BaseTzInfo:
    try:
        return pytz.timezone(tz_string)
    except pytz.exceptions.UnknownTimeZoneError:
        raise ValueError(f"Invalid timezone in config: '{tz_string}'. Must be a valid IANA timezone name")


def parse_config(config_path: Path):
    """
    Reads config file and returns Orchestrator parameters.
    """
    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)

    config = Config.model_validate(raw)

    timezone = parse_timezone(config.db_timezone)

    scheduler = ReportScheduler(
        config.schedule.build(timezone),
        [
            TrafficVolumeGenerator(config.service_name, config.short_service, config.query_executor.build()),
            TrafficSizesGenerator(config.service_name, config.short_service, config.query_executor.build()),
            RCodeVolumeGenerator(config.service_name, config.short_service, config.query_executor.build()),
            UniqueSourcesGenerator(config.service_name, config.short_service, config.query_executor.build()),
        ],
    )

    return (Path(config.export_root), config.per_ns_mode, scheduler)
