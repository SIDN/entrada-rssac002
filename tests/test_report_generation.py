import datetime
import unittest

from loguru import logger

from src.customexceptions import NoDataException
from src.generators.RCodeVolumeGenerator import RCodeVolumeGenerator
from src.generators.TrafficSizesGenerator import TrafficSizesGenerator
from src.generators.TrafficVolumeGenerator import TrafficVolumeGenerator
from src.generators.UniqueSourcesGenerator import UniqueSourcesGenerator
from src.reports.reports import RCodeVolumeReport, TrafficSizesReport, TrafficVolumeReport, UniqueSourcesReport
from tests.data_generation import SyntheticDataGenerator
from tests.database_setup import connect_database, setup_table
from tests.server_data import ServerData

DAY = datetime.date(year=2000, month=1, day=2)

# Ranges are in local time, following the database.
START = datetime.datetime(
    year=DAY.year, month=DAY.month, day=DAY.day, hour=0, minute=0, second=0, tzinfo=datetime.timezone.utc
).astimezone()
END = datetime.datetime(
    year=DAY.year, month=DAY.month, day=DAY.day + 1, hour=0, minute=0, second=0, tzinfo=datetime.timezone.utc
).astimezone()


class ReportGenerationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        logger.remove()
        self.query_executor = await connect_database()
        data_generator = SyntheticDataGenerator(self.query_executor)
        await data_generator.populate_database(date=DAY, data_volume=250, servers=4)
        self.server_data: dict[str, ServerData] = data_generator.get_expected_reports_with_service("test")

    async def test_rcode_volume(self):
        g = RCodeVolumeGenerator("test", "short_service", self.query_executor)
        reports: list[RCodeVolumeReport] = await g.generate_reports(START, END)

        for report in reports:
            service_name = report.service
            rcodes = report.rcode_volume
            self.assertDictEqual(rcodes, self.server_data[service_name].rcode_volume)

    async def test_traffic_volume(self):
        g = TrafficVolumeGenerator("test", "short_service", self.query_executor)
        reports: list[TrafficVolumeReport] = await g.generate_reports(START, END)

        for report in reports:
            service_name = report.service
            xp_dict = {
                "dns-udp-queries-received-ipv4": report.dns_udp_queries_received_ipv4,
                "dns-udp-queries-received-ipv6": report.dns_udp_queries_received_ipv6,
                "dns-tcp-queries-received-ipv4": report.dns_tcp_queries_received_ipv4,
                "dns-tcp-queries-received-ipv6": report.dns_tcp_queries_received_ipv6,
                "dns-udp-responses-sent-ipv4": report.dns_udp_responses_sent_ipv4,
                "dns-udp-responses-sent-ipv6": report.dns_udp_responses_sent_ipv6,
                "dns-tcp-responses-sent-ipv4": report.dns_tcp_responses_sent_ipv4,
                "dns-tcp-responses-sent-ipv6": report.dns_tcp_responses_sent_ipv6,
            }

            self.assertDictEqual(xp_dict, self.server_data[service_name].traffic_volume)

    async def test_traffic_sizes(self):
        g = TrafficSizesGenerator("test", "short_service", self.query_executor)
        reports: list[TrafficSizesReport] = await g.generate_reports(START, END)

        for report in reports:
            service_name = report.service
            xp_dict = {
                "udp-request-sizes": report.udp_request_sizes,
                "udp-response-sizes": report.udp_response_sizes,
                "tcp-request-sizes": report.tcp_request_sizes,
                "tcp-response-sizes": report.tcp_response_sizes,
            }

            self.assertDictEqual(xp_dict, self.server_data[service_name].traffic_sizes)

    async def test_unique_sources(self):
        g = UniqueSourcesGenerator("test", "short_service", self.query_executor)
        reports: list[UniqueSourcesReport] = await g.generate_reports(START, END)

        for report in reports:
            service_name = report.service
            xp_dict = {
                "num-sources-ipv4": report.num_sources_ipv4,
                "num-sources-ipv6": report.num_sources_ipv6,
                "num-sources-ipv6-aggregate": report.num_sources_ipv6_aggregate,
            }

            self.assertDictEqual(xp_dict, self.server_data[service_name].unique_sources)

    async def asyncTearDown(self) -> None:
        await self.query_executor.close()


class NoDataTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.query_executor = await connect_database()
        await self.query_executor.execute("DROP TABLE IF EXISTS dns", None)
        await self.query_executor.execute(setup_table(), None)

    async def test_empty_rcodes(self):
        gen = [
            RCodeVolumeGenerator("test", "", self.query_executor),
            TrafficVolumeGenerator("test", "", self.query_executor),
            TrafficSizesGenerator("test", "", self.query_executor),
            UniqueSourcesGenerator("test", "", self.query_executor),
        ]

        expected = [
            {},
            {
                "dns-udp-queries-received-ipv4": 0,
                "dns-udp-queries-received-ipv6": 0,
                "dns-tcp-queries-received-ipv4": 0,
                "dns-tcp-queries-received-ipv6": 0,
                "dns-udp-responses-sent-ipv4": 0,
                "dns-udp-responses-sent-ipv6": 0,
                "dns-tcp-responses-sent-ipv4": 0,
                "dns-tcp-responses-sent-ipv6": 0,
            },
            {"tcp-request-sizes": {}, "tcp-response-sizes": {}, "udp-request-sizes": {}, "udp-response-sizes": {}},
            {"num-sources-ipv4": 0, "num-sources-ipv6": 0, "num-sources-ipv6-aggregate": 0},
        ]

        for g, xp in list(zip(gen, expected)):
            with self.assertRaises(NoDataException):
                await g.generate_per_ns(START, END)

            res = await g.generate_reports(START, END)
            self.assertEqual(len(res), 1)
            report = res[0]
            self.assertEqual(report.service, "test")
            self.assertDictEqual(xp, report.fields)

            res_2 = await g.generate_report(START, END)
            self.assertEqual(res_2.service, "test")
            self.assertDictEqual(xp, res_2.fields)

    async def asyncTearDown(self) -> None:
        await self.query_executor.close()


if __name__ == "__main__":
    unittest.main()
