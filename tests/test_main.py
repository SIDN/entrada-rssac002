import asyncio
import datetime
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from loguru import logger

from src.customexceptions import PermanentError
from src.main import Orchestrator, main
from src.run_all_queries import run_all_queries
from src.querying.query_executors import SQLiteQueryExecutor
from tests.database_setup import fill_in_table, setup_table


class MainTests(unittest.TestCase):

    def setUp(self):
        logger.remove()

    def test_scheduler_permanent_error(self):
        with (
            self.assertRaises(PermanentError),
            patch("src.scheduling.scheduler.ReportScheduler") as mock_scheduler
        ):  
            mock_scheduler.start.side_effect = PermanentError
            
            o = Orchestrator('/', True, mock_scheduler)
            asyncio.run(o.start())

    def test_one_shot_runs_one_scheduled_batch(self):
        scheduler = MagicMock()
        scheduler.start = AsyncMock(return_value=[])
        orchestrator = Orchestrator('/', True, scheduler)

        with patch("src.main.ReportExporter.export_reports"):
            asyncio.run(orchestrator.start_once())

        scheduler.start.assert_awaited_once_with(per_ns=True)

    def test_scheduler_flag_is_not_passed_to_scheduler_argument_parser(self):
        scheduler = MagicMock()
        with (
            patch("sys.argv", ["main.py", "--scheduler", "--config", "config.yaml", "--once"]),
            patch("src.main.parse_config", return_value=(Path("config.yaml"), True, scheduler)),
            patch("src.main.Orchestrator"),
            patch("src.main.asyncio.run") as run,
        ):
            main()

        run.assert_called_once()

    def test_run_all_queries_executes_all_query_methods(self):
        async def run_test() -> None:
            executor = SQLiteQueryExecutor(tld="nl")
            await executor.execute("DROP TABLE IF EXISTS dns", ())
            await executor.execute(setup_table(), ())

            start = datetime.datetime(2026, 5, 21, 0, 0, 0)
            end = datetime.datetime(2026, 5, 21, 23, 59, 59)
            await executor.execute(
                fill_in_table(),
                (
                    0,
                    start,
                    17,
                    4,
                    128,
                    512,
                    "192.0.2.1",
                    "default-ns",
                ),
            )

            results = await run_all_queries(executor, start, end, "nl")

            self.assertIn("rcode_volume_global", results)
            self.assertIn("traffic_volume_global", results)
            self.assertIn("unique_sources_global", results)
            self.assertTrue(results["rcode_volume_global"])

            await executor.close()

        asyncio.run(run_test())

