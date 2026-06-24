import datetime
import ipaddress
import math
import random
import unittest

from loguru import logger

from src.generators.RCodeVolumeGenerator import RCodeVolumeGenerator
from src.generators.TrafficSizesGenerator import TrafficSizesGenerator
from src.generators.TrafficVolumeGenerator import TrafficVolumeGenerator
from src.generators.UniqueSourcesGenerator import UniqueSourcesGenerator
from src.reports.histogramutils import REQUEST_BUCKETS, RESPONSE_BUCKETS
from tests.database_setup import connect_database, fill_in_table, setup_table

# Test data volume
RECORDS = 1000
ABSENT_RECORDS_LIMITER = 10


class RSSAC002Tests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        logger.remove()
        self.start = datetime.datetime(2026, 5, 21, 0, 0, 0)
        self.end = datetime.datetime(2026, 5, 21, 23, 59, 59)

        self.query_executor = await connect_database()

        await self.query_executor.execute("DROP TABLE IF EXISTS dns", None)
        await self.query_executor.execute(setup_table(), None)

        self.time_difference = self.end - self.start

        self.rcodes = [0] * 16

        self.prot = [17, 6]
        self.ipv = [4, 6]

        self.query_type_counts = [0, 0, 0, 0, 0, 0, 0, 0]

        # Histograms to populate randomly and assert together with the query results later
        self.request_hist_udp = [0] * (math.ceil(288 / 16) + 1)
        self.response_hist_udp = [0] * (math.ceil(4096 / 16) + 1)
        self.request_hist_tcp = [0] * (math.ceil(288 / 16) + 1)
        self.response_hist_tcp = [0] * (math.ceil(4096 / 16) + 1)

        self.unique_ipv4 = random.randrange(1, 300)
        self.unique_ipv6 = random.randrange(1, 300)

        # IP address sources
        self.ipv4_sources = [""] * self.unique_ipv4
        self.ipv6_sources = [""] * self.unique_ipv6
        self.expected_ipv4_sources = set()
        self.expected_ipv6_sources = set()
        self.expected_ipv6_aggregates = set()

        for i in range(0, len(self.ipv4_sources)):
            self.ipv4_sources[i] = str(ipaddress.IPv4Address(random.getrandbits(32)))

        for i in range(len(self.ipv6_sources)):
            self.ipv6_sources[i] = str(ipaddress.IPv6Address(random.getrandbits(128)))

        await self.keep_track_of_generated_data()

        self.setUpTests()

    async def keep_track_of_generated_data(self):
        """
        Generates fake data and keeps track of it, this includes:
            Choosing a random rcode and populating a histogram with it
            Choosing protocol, ip version and whether it is a request or response
            Populating histogram for each query type
            Generating packet lengths
            Generating ip addresses based on the version
        """
        for i in range(0, RECORDS):
            # List that acts as a histogram to keep track of the rcodes to make assertions
            rcode = random.randrange(0, len(self.rcodes))
            self.rcodes[rcode] += 1

            # Seed keeps track of the different protocols/ip version used and whether it is a request or a response
            # used to make the right assertions
            protocol = random.choice([0, 1])
            version = random.choice([0, 1])
            request_or_response = random.choice([0, 1])
            seed = protocol + version * 2 + request_or_response * 2 * 2
            self.query_type_counts[seed] += 1

            # Histograms are separated by protocol
            if protocol == 0:
                request_histogram = self.request_hist_udp
                response_histogram = self.response_hist_udp
            else:
                request_histogram = self.request_hist_tcp
                response_histogram = self.response_hist_tcp

            # Packet length depends on query type
            if request_or_response == 0:
                received_length = random.randrange(1, 600)
                response_length = None

                # Populate request histogram according to random lengths
                if received_length < 288:
                    request_histogram[math.floor(received_length / 16)] += 1
                else:
                    request_histogram[math.floor(288 / 16)] += 1
            else:
                received_length = None
                response_length = random.randrange(1, 6000)

                # Populate response histogram according to random lengths
                if response_length < 4096:
                    response_histogram[math.floor(response_length / 16)] += 1
                else:
                    response_histogram[math.floor(4096 / 16)] += 1

            if version == 0:
                ip_address = random.choice(self.ipv4_sources)
                self.expected_ipv4_sources.add(ip_address)
            else:
                ip_address = random.choice(self.ipv6_sources)
                self.expected_ipv6_sources.add(ip_address)

                network = ipaddress.IPv6Network(f"{ip_address}/64", strict=False)
                self.expected_ipv6_aggregates.add(network)

            await self.create_record(
                i, rcode, protocol, version, received_length, response_length, ip_address, "default-ns"
            )

    async def create_record(
        self, index, rcode, protocol, version, received_length, response_length, ip_address, server
    ):
        """
        Creates a record in the database based on the generated data
        Records that fall outside of the time range will also be generated, but they will be generated less frequently
        """
        # Records that will be included in the timerange
        params = [
            rcode,
            (self.start + datetime.timedelta(seconds=random.randrange(0, self.time_difference.seconds))),
            self.prot[protocol],
            self.ipv[version],
            received_length,
            response_length,
            ip_address,
            server,
        ]
        await self.query_executor.execute(fill_in_table(), params)

        # Records that won't be included in the timerange
        if index == RECORDS / ABSENT_RECORDS_LIMITER:
            params = [
                rcode,
                (self.end + datetime.timedelta(seconds=random.randrange(0, 100 * self.time_difference.seconds))),
                self.prot[protocol],
                self.ipv[version],
                received_length,
                response_length,
                ip_address,
                server,
            ]
            await self.query_executor.execute(fill_in_table(), params)
            params = [
                rcode,
                (self.start - datetime.timedelta(seconds=random.randrange(0, 100 * self.time_difference.seconds))),
                self.prot[protocol],
                self.ipv[version],
                received_length,
                response_length,
                ip_address,
                server,
            ]
            await self.query_executor.execute(fill_in_table(), params)

    async def asyncTearDown(self) -> None:
        await self.query_executor.close()


class RCodeVolumeTests(RSSAC002Tests):
    def setUpTests(self):
        self.rcode_volume_generator = RCodeVolumeGenerator("SIDN", "short_service", self.query_executor)

    async def test_rcode_volume_generation(self):
        report = await self.rcode_volume_generator.generate_report(self.start, self.end)

        self.assertEqual(report.metric, "rcode-volume")

        for r in self.rcodes:
            if r in report.rcode_volume:
                self.assertEqual(report.rcode_volume[r], self.rcodes[r])

    async def test_rcode_volume_sorted_keys(self):
        report = await self.rcode_volume_generator.generate_report(self.start, self.end)

        keys_list = list(report.rcode_volume.keys())
        i = 0

        for r in self.rcodes:
            if r in report.rcode_volume:
                self.assertEqual(keys_list[i + 1], r)
                i += 1


class TrafficVolumeTests(RSSAC002Tests):
    def setUpTests(self):
        self.traffic_volume_generator = TrafficVolumeGenerator("SIDN", "short_service", self.query_executor)

    async def test_traffic_volume_generation(self):
        report = await self.traffic_volume_generator.generate_report(self.start, self.end)

        self.assertEqual(report.metric, "traffic-volume")
        self.assertEqual(report.dns_udp_queries_received_ipv4, self.query_type_counts[0])
        self.assertEqual(report.dns_udp_queries_received_ipv6, self.query_type_counts[2])
        self.assertEqual(report.dns_tcp_queries_received_ipv4, self.query_type_counts[1])
        self.assertEqual(report.dns_tcp_queries_received_ipv6, self.query_type_counts[3])

        self.assertEqual(report.dns_udp_responses_sent_ipv4, self.query_type_counts[4])
        self.assertEqual(report.dns_udp_responses_sent_ipv6, self.query_type_counts[6])
        self.assertEqual(report.dns_tcp_responses_sent_ipv4, self.query_type_counts[5])
        self.assertEqual(report.dns_tcp_responses_sent_ipv6, self.query_type_counts[7])


class TrafficSizesTests(RSSAC002Tests):
    def setUpTests(self):
        self.traffic_sizes_generator = TrafficSizesGenerator("SIDN", "short_service", self.query_executor)

    async def test_traffic_sizes_generation(self):
        report = await self.traffic_sizes_generator.generate_report(self.start, self.end)

        self.assertEqual(report.metric, "traffic-sizes")

        self.assertEqual(
            set(report.udp_request_sizes.keys()).intersection(REQUEST_BUCKETS), set(report.udp_request_sizes.keys())
        )
        self.assertEqual(
            set(report.udp_response_sizes.keys()).intersection(RESPONSE_BUCKETS), set(report.udp_response_sizes.keys())
        )
        self.assertEqual(
            set(report.tcp_request_sizes.keys()).intersection(REQUEST_BUCKETS), set(report.tcp_request_sizes.keys())
        )
        self.assertEqual(
            set(report.tcp_response_sizes.keys()).intersection(RESPONSE_BUCKETS), set(report.tcp_response_sizes.keys())
        )


class UniqueSourcesTests(RSSAC002Tests):
    def setUpTests(self):
        self.unique_sources_generator = UniqueSourcesGenerator("SIDN", "short_service", self.query_executor)

    async def test_unique_sources_generation(self):
        report = await self.unique_sources_generator.generate_report(self.start, self.end)

        self.assertEqual(report.metric, "unique-sources")
        self.assertEqual(report.num_sources_ipv4, len(self.expected_ipv4_sources))
        self.assertEqual(report.num_sources_ipv6, len(self.expected_ipv6_sources))
        self.assertEqual(report.num_sources_ipv6_aggregate, len(self.expected_ipv6_aggregates))


if __name__ == "__main__":
    unittest.main()
