import argparse
import asyncio
import datetime
from pathlib import Path

import yaml
from loguru import logger

from src.config.config_parser import Config, parse_timezone
from src.exporting.report_exporting import ReportExporter
from src.generators.RCodeVolumeGenerator import RCodeVolumeGenerator
from src.generators.TrafficSizesGenerator import TrafficSizesGenerator
from src.generators.TrafficVolumeGenerator import TrafficVolumeGenerator
from src.generators.UniqueSourcesGenerator import UniqueSourcesGenerator
from src.run_unique_sources import daily_windows, make_export_closure, parse_date


def run_all_metrics(
    config_path: Path,
    start_date: datetime.date,
    end_date: datetime.date,
    overwrite_existing: bool = False,
) -> None:
    with config_path.open() as config_file:
        config = Config.model_validate(yaml.safe_load(config_file))

    database_timezone = parse_timezone(config.db_timezone)
    windows = daily_windows(start_date, end_date, database_timezone)
    query_executor = config.query_executor.build(config.tld_evaluated)
    generators = [
        TrafficVolumeGenerator(config.service_name, config.short_service, query_executor),
        TrafficSizesGenerator(config.service_name, config.short_service, query_executor),
        RCodeVolumeGenerator(config.service_name, config.short_service, query_executor),
        UniqueSourcesGenerator(config.service_name, config.short_service, query_executor),
    ]
    exporter = ReportExporter()
    export_root = Path(config.export_root)

    async def generate_each_day() -> None:
        for start, end in windows:
            logger.info(f"Generating all configured metrics for {start.date()}.")
            for generator in generators:
                if config.per_ns_mode:
                    reports = await generator.generate_reports(start, end)
                else:
                    reports = [await generator.generate_report(start, end)]

                for report in reports:
                    exporter.export_report(make_export_closure(report, export_root, overwrite_existing))

    asyncio.run(generate_each_day())


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate all configured metric YAML reports for each day in a range.")
    parser.add_argument("--config", type=Path, default=Path("rssac002config.yaml"))
    parser.add_argument("--start", type=parse_date, required=True, help="First day to report, inclusive (YYYY-MM-DD)")
    parser.add_argument("--end", type=parse_date, required=True, help="Last day to report, inclusive (YYYY-MM-DD)")
    parser.add_argument("--overwrite", action="store_true", help="Atomically replace existing daily YAML reports")
    arguments = parser.parse_args()

    if arguments.end < arguments.start:
        parser.error("--end must be on or after --start")

    run_all_metrics(arguments.config, arguments.start, arguments.end, arguments.overwrite)


if __name__ == "__main__":
    main()