import datetime
import unittest
from unittest.mock import AsyncMock, MagicMock

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

    async def test_null_rcode_global(self):
        """A NULL rcode in the global query is reported as -1."""
        start = datetime.datetime(2026, 5, 21, 0, 0, 0, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(2026, 5, 22, 0, 0, 0, tzinfo=datetime.timezone.utc)
        self.mock_query_executor.query_rcode_volume_global = AsyncMock(
            return_value=[{"dns_rcode": None, "_col1": 3}, {"dns_rcode": 0, "_col1": 5}]
        )

        report = await self.generators[0].generate_report(start, end)

        self.assertDictEqual(report.rcode_volume, {-1: 3, 0: 5})

    async def test_null_rcode_per_ns(self):
        """A NULL rcode in the per-nameserver query is reported as -1, also in the aggregated report."""
        start = datetime.datetime(2026, 5, 21, 0, 0, 0, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(2026, 5, 22, 0, 0, 0, tzinfo=datetime.timezone.utc)
        self.mock_query_executor.query_rcode_volume_per_ns = AsyncMock(
            return_value=[
                {"server": "ns1", "dns_rcode": None, "_col2": 3},
                {"server": "ns1", "dns_rcode": 0, "_col2": 5},
                {"server": "ns2", "dns_rcode": None, "_col2": 2},
            ]
        )

        reports = await self.generators[0].generate_reports(start, end)

        self.assertDictEqual({report.service: report.rcode_volume for report in reports}, {
            "SIDN-ns1": {-1: 3, 0: 5},
            "SIDN-ns2": {-1: 2},
            "SIDN": {-1: 5, 0: 5},
        })
