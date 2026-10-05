import argparse
import asyncio
import sys
from pathlib import Path

import yaml
from loguru import logger
from pydantic import ValidationError

from src.config.config_parser import parse_config
from src.customexceptions import PermanentError
from src.exporting.report_exporting import ReportExporter
from src.reports.reports import Report
from src.scheduling.scheduler import ReportScheduler


class Orchestrator:
    """Orchestrator class for RSSAC002-style report generation."""

    def __init__(self, export_root: Path, per_ns_mode: bool, scheduler: ReportScheduler) -> None:
        """
        export_root: base path for report exporting
        per_ns_mode: is generation per nameserver or just global?
        scheduler: object for scheduling report generation
        """
        self.__export_root: Path = export_root
        self.__per_ns_mode = per_ns_mode
        self.__scheduler = scheduler
        self.__exporter = ReportExporter()

    async def start(self) -> None:
        """
        > Do forever:
            1. Generate reports.
            2. Export reports.
        """
        while True:
            await self.__run_batch()

    async def start_once(self) -> None:
        """Generate and export one scheduled report batch, then exit."""
        await self.__run_batch()
        logger.info("Single report batch completed.")

    async def __run_batch(self) -> None:
        try:
            reports: list[Report] = await self.__scheduler.start(per_ns=self.__per_ns_mode)
            self.__exporter.export_reports(reports, self.__export_root)
        except PermanentError as e:
            logger.critical(f"Exiting program due to permanent error: {str(e)}")
            raise


def parse_args(argv: list[str] | None = None) -> tuple[Path, bool]:
    """Parses command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", action="store_true")
    parser.add_argument("-c", "--config", type=str)
    parser.add_argument("--once", action="store_true", help="generate one report batch and exit")
    args = parser.parse_args(argv)

    if args.debug:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.remove()
        logger.add(sys.stderr, level="INFO")
    if args.config:
        config_path = Path(args.config)
    else:
        config_path = Path("rssac002config.yaml")

    return config_path, args.once


def main():
    """Default entrypoint: run the one-shot query suite unless scheduler mode is explicitly requested."""
    entry_parser = argparse.ArgumentParser(add_help=False)
    entry_parser.add_argument(
        "--scheduler",
        action="store_true",
        help="Run the long-lived report scheduler instead of the query runner.",
    )
    entry_args, runner_args = entry_parser.parse_known_args()

    if entry_args.scheduler:
        config_path, run_once = parse_args(runner_args)
        try:
            orchestrator = Orchestrator(*parse_config(config_path))
            if run_once:
                asyncio.run(orchestrator.start_once())
            else:
                asyncio.run(orchestrator.start())
        except ValidationError as e:
            logger.error("Validation error while reading config file.")
            logger.error(str(e))
        except FileNotFoundError as e:
            logger.error("File ./rssac002config.yaml was not found.")
            logger.error(str(e))
        except IOError as e:
            logger.error("Something went wrong during reading rssac002config.yaml")
            logger.error(str(e))
        except yaml.YAMLError as e:
            logger.error("Config is not valid YAML.")
            logger.error(str(e))
        except KeyboardInterrupt:
            logger.critical("KeyboardInterrupt: Exiting...")
        return

    from src.run_all_queries import main as run_all_queries_main

    run_all_queries_main()


if __name__ == "__main__":
    main()