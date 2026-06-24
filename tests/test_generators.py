import datetime
import unittest
from unittest.mock import MagicMock

from src.customexceptions import DateRangeError
from src.generators.RCodeVolumeGenerator import RCodeVolumeGenerator
from src.generators.TrafficSizesGenerator import TrafficSizesGenerator
from src.generators.TrafficVolumeGenerator import TrafficVolumeGenerator
from src.generators.UniqueSourcesGenerator import UniqueSourcesGenerator


class RSSAC002Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_query_executor = MagicMock()

        self.generators = [
            RCodeVolumeGenerator("SIDN", ".nl", self.mock_query_executor),
            TrafficVolumeGenerator("SIDN", ".nl", self.mock_query_executor),
            TrafficSizesGenerator("SIDN", ".nl", self.mock_query_executor),
            UniqueSourcesGenerator("SIDN", ".nl", self.mock_query_executor),
        ]

    async def test_incorrect_daterange(self):
        for generator in self.generators:
            incorrect_start = datetime.datetime(2026, 5, 21, 2, 0, 0)
            incorrect_end = datetime.datetime(2026, 5, 21, 0, 0, 0)

            with self.assertRaises(DateRangeError):
                await generator.generate_report(incorrect_start, incorrect_end)

    def test_metadata_generation(self):
        for generator in self.generators:
            start = datetime.datetime(2026, 5, 21, 0, 0, 0, tzinfo=datetime.timezone.utc)
            report = generator.generate_metadata(start)

            self.assertEqual(report["version"], "rssac002v5")
            self.assertEqual(report["service"], "SIDN")
            self.assertEqual(report["start_period"], start)
            self.assertEqual(report["short_service"], ".nl")
