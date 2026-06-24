import os
import shutil
import unittest
from datetime import date, datetime
from pathlib import Path

from loguru import logger

from src.generators.RCodeVolumeGenerator import RCodeVolumeGenerator
from src.generators.TrafficSizesGenerator import TrafficSizesGenerator
from src.generators.TrafficVolumeGenerator import TrafficVolumeGenerator
from src.generators.UniqueSourcesGenerator import UniqueSourcesGenerator
from src.main import Orchestrator
from src.querying.query_executors import SQLiteQueryExecutor
from src.scheduling.scheduler import ReportScheduler
from tests.data_generation import SyntheticDataGenerator
from tests.TimeMocking import StopApplication, TimeMock

TEST_ROOT = Path("RSSAC002-test-data")


class OrchestratorDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """Populate database with test data. Construct schedule and orchestrator."""
        logger.remove()
        self.query_executor = SQLiteQueryExecutor()
        gen = SyntheticDataGenerator(self.query_executor)

        # populate database for 3 days
        await gen.populate_database(date(year=2000, month=1, day=1), 10, 4)
        self.day1_data = gen.server_data
        await gen.populate_database(date(year=2000, month=1, day=2), 10, 4)
        self.day2_data = gen.server_data
        await gen.populate_database(date(year=2000, month=1, day=3), 10, 4)
        self.day3_data = gen.server_data

        self.name = "test_service"
        self.short = "test_short_service"

    async def test_normal(self):
        time_mock: TimeMock = TimeMock(3, datetime(year=2000, month=1, day=2, hour=2, minute=59, second=59))
        TimeMock.set_stop_count(1)
        scheduler = ReportScheduler(
            time_mock.make_schedule(),
            [
                TrafficVolumeGenerator(self.name, self.short, self.query_executor),
                TrafficSizesGenerator(self.name, self.short, self.query_executor),
                RCodeVolumeGenerator(self.name, self.short, self.query_executor),
                UniqueSourcesGenerator(self.name, self.short, self.query_executor),
            ],
            *time_mock.make_time(),
        )

        orchestrator = Orchestrator(TEST_ROOT, True, scheduler)
        try:
            await orchestrator.start()
        except StopApplication:
            metrics = ["rcode-volume", "traffic-sizes", "traffic-volume", "unique-sources"]
            expected_files = []

            for metric in metrics:
                loc = TEST_ROOT / "2000" / "01" / metric
                expected_files.extend(
                    [
                        loc / f"test_short_service-{20000101}-{metric}.yaml",
                        loc / f"test_short_service-{20000102}-{metric}.yaml",
                        loc / f"test_short_service-{20000103}-{metric}.yaml",
                    ]
                )
                for i in range(1, 4 + 1):
                    expected_files.extend(
                        [
                            loc / 'nameservers' / f"test_short_service-{i}-{20000101}-{metric}.yaml",
                            loc / 'nameservers' / f"test_short_service-{i}-{20000102}-{metric}.yaml",
                            loc / 'nameservers' / f"test_short_service-{i}-{20000103}-{metric}.yaml",
                        ]
                    )

            for filepath in expected_files:
                self.assertTrue(filepath.exists(), filepath)

    async def asyncTearDown(self) -> None:
        await self.query_executor.close()
        if os.path.exists(TEST_ROOT):
            shutil.rmtree(TEST_ROOT)


if __name__ == "__main__":
    unittest.main()
