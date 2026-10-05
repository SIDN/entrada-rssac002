import argparse
import asyncio
import datetime
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from src.config.config_parser import Config, parse_timezone
from src.exporting.report_exporting import ReportExporter
from src.generators.RCodeVolumeGenerator import RCodeVolumeGenerator
from src.generators.TrafficSizesGenerator import TrafficSizesGenerator
from src.generators.TrafficVolumeGenerator import TrafficVolumeGenerator
from src.generators.UniqueSourcesGenerator import UniqueSourcesGenerator
from src.querying.query_executors import QueryExecutor, SQLiteQueryExecutor
from src.run_unique_sources import daily_windows, make_export_closure, parse_date


async def run_all_queries(
    query_executor: QueryExecutor,
    start: datetime.datetime,
    end: datetime.datetime,
    tld: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Execute every query in the current query catalog for a single time range."""
    params = (start, end)
    tld_value = tld or query_executor.tld
    query_methods = {
        "rcode_volume_global": query_executor.query_rcode_volume_global,
        "rcode_volume_per_ns": query_executor.query_rcode_volume_per_ns,
        "unique_sources_global": query_executor.query_unique_sources_global,
        "unique_sources_per_ns": query_executor.query_unique_sources_per_ns,
        "traffic_volume_global": query_executor.query_traffic_volume_global,
        "traffic_volume_per_ns": query_executor.query_traffic_volume_per_ns,
        "traffic_sizes_global_request": query_executor.query_traffic_sizes_global_request,
        "traffic_sizes_per_ns_request": query_executor.query_traffic_sizes_per_ns_request,
        "traffic_sizes_global_response": query_executor.query_traffic_sizes_global_response,
        "traffic_sizes_per_ns_response": query_executor.query_traffic_sizes_per_ns_response,
    }

    results: dict[str, list[dict[str, Any]]] = {}
    for name, method in query_methods.items():
        results[name] = await method(params)

    if not tld_value:
        raise ValueError("A TLD value is required to run the query catalog.")

    return results


def build_executor(config_path: Path, tld: str | None, sqlite_mode: bool) -> QueryExecutor:
    if sqlite_mode:
        return SQLiteQueryExecutor(tld=tld or "example")

    with config_path.open() as config_file:
        config = Config.model_validate(yaml.safe_load(config_file))

    return config.query_executor.build(tld or config.tld_evaluated)


async def generate_reports_for_range(
    config_path: Path,
    start_date: datetime.date,
    end_date: datetime.date,
    *,
    tld: str | None = None,
    sqlite_mode: bool = False,
    overwrite_existing: bool = False,
) -> None:
    """Generate and export YAML report files for the requested date range."""
    if sqlite_mode:
        config = None
        executor = SQLiteQueryExecutor(tld=tld or "example")
        export_root = Path("./sqlite-export")
        per_ns_mode = True
    else:
        with config_path.open() as config_file:
            config = Config.model_validate(yaml.safe_load(config_file))
        executor = config.query_executor.build(tld or config.tld_evaluated)
        export_root = Path(config.export_root)
        per_ns_mode = config.per_ns_mode

    database_timezone = parse_timezone(config.db_timezone) if config is not None else datetime.timezone.utc
    windows = daily_windows(start_date, end_date, database_timezone)
    generators = [
        TrafficVolumeGenerator((config.service_name if config is not None else "default-service"), (config.short_service if config is not None else tld or "example"), executor),
        TrafficSizesGenerator((config.service_name if config is not None else "default-service"), (config.short_service if config is not None else tld or "example"), executor),
        RCodeVolumeGenerator((config.service_name if config is not None else "default-service"), (config.short_service if config is not None else tld or "example"), executor),
        UniqueSourcesGenerator((config.service_name if config is not None else "default-service"), (config.short_service if config is not None else tld or "example"), executor),
    ]
    exporter = ReportExporter()

    for start, end in windows:
        logger.info(f"Generating configured metrics for {start.date()}.")
        for generator in generators:
            if per_ns_mode:
                reports = await generator.generate_reports(start, end)
            else:
                reports = [await generator.generate_report(start, end)]

            for report in reports:
                exporter.export_report(make_export_closure(report, export_root, overwrite_existing))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate RSSAC002 YAML reports for a date range without starting the scheduler loop.")
    parser.add_argument("--config", type=Path, default=Path("rssac002config.yaml"), help="YAML config file to use for connection details.")
    parser.add_argument("--start", type=parse_date, required=True, help="First date to generate, inclusive (YYYY-MM-DD)")
    parser.add_argument("--end", type=parse_date, required=True, help="Last date to generate, inclusive (YYYY-MM-DD)")
    parser.add_argument("--tld", default=None, help="TLD to evaluate. Defaults to the config value when not using --sqlite.")
    parser.add_argument("--overwrite", action="store_true", help="Atomically replace existing report files")
    parser.add_argument("--sqlite", action="store_true", help="Use the in-memory SQLite executor instead of the configured query engine.")
    args = parser.parse_args()

    if args.end < args.start:
        parser.error("--end must be on or after --start")

    asyncio.run(
        generate_reports_for_range(
            args.config,
            args.start,
            args.end,
            tld=args.tld,
            sqlite_mode=args.sqlite,
            overwrite_existing=args.overwrite,
        )
    )


if __name__ == "__main__":
    main()
