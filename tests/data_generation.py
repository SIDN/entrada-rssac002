import datetime
import ipaddress
import random
from collections import defaultdict
from typing import Any

import numpy as np

from src.reports.histogramutils import REQUEST_BUCKETS, RESPONSE_BUCKETS
from tests.database_setup import fill_in_table, setup_table

from .server_data import ServerData, get_global_report


class SyntheticDataGenerator:
    def __init__(self, query_executor):
        self.query_executor = query_executor

    async def populate_database(self, date: datetime.date, data_volume, servers: int):
        await self.query_executor.execute(setup_table(), None)

        assert servers > 0

        self.server_data: dict[str, ServerData] = await self.generate_per_server(date, data_volume, servers)

    async def generate_per_server(self, date: datetime.date, data_volume: int, servers: int) -> dict[str, ServerData]:
        server_dict: dict[str, ServerData] = {}
        for server in range(1, servers + 1):
            (rows, traffic_volume, traffic_sizes, rcode_volume, unique_sources) = self.generate_rows(date, data_volume)
            server_dict[str(server)] = ServerData(traffic_volume, traffic_sizes, rcode_volume, unique_sources)

            for row in rows:
                await self.create_record(*row, str(server))

        global_report: ServerData = get_global_report(list(server_dict.values()))
        server_dict[""] = global_report

        return server_dict

    def generate_rows(self, date: datetime.date, data_volume: int):
        """
        > Generates a data distribution, as well as the expected RSSAC002 reports.
        > Takes a DATA_VOLUME parameter which dictates how many datapoints should be recorded.
        > For simplicity purposes, the first version of this method assumes that each record consists
        of request + response data, which is in practice not always the case, as some records contain
        NULL for either value. This would reflect for example an unanswered request.
        > Distributes DATA_VOLUME over UDP_VOLUME and TCP_VOLUME
            under the assumption above (|PROTOCOL_REQUESTS| = |PROTOCOL_RESPONSES|)
        > Distributes protocol volumes over PROTOCOL_IPV4 and PROTOCOL_IPV6.
        > Randomly generates traffic-sizes histograms, ensuring that the sum of histogram observations adds up
            to protocol volume.
        > Randomly generates unique-sources distributions, with upper bound being the total IP version sources.
        > Randomly generates rcode-volume distribution, with total  sum being the DATA_VOLUME.
        """

        def random_numbers_with_sum(n, total) -> list[int]:
            return np.random.multinomial(total, [1 / n] * n).tolist()

        [UDP_VOLUME, TCP_VOLUME] = random_numbers_with_sum(2, data_volume)
        [UDP_IPV4, UDP_IPV6] = random_numbers_with_sum(2, UDP_VOLUME)
        [TCP_IPV4, TCP_IPV6] = random_numbers_with_sum(2, TCP_VOLUME)

        traffic_volume = {
            "dns-udp-queries-received-ipv4": UDP_IPV4,
            "dns-udp-queries-received-ipv6": UDP_IPV6,
            "dns-tcp-queries-received-ipv4": TCP_IPV4,
            "dns-tcp-queries-received-ipv6": TCP_IPV6,
            "dns-udp-responses-sent-ipv4": UDP_IPV4,
            "dns-udp-responses-sent-ipv6": UDP_IPV6,
            "dns-tcp-responses-sent-ipv4": TCP_IPV4,
            "dns-tcp-responses-sent-ipv6": TCP_IPV6,
        }

        # Generate traffic-sizes distribution histograms
        UDP_REQUEST_SIZES_HIST = self.generate_request_hist(REQUEST_BUCKETS, UDP_VOLUME)
        TCP_REQUEST_SIZES_HIST = self.generate_request_hist(REQUEST_BUCKETS, TCP_VOLUME)
        UDP_RESPONSE_SIZES_HIST = self.generate_request_hist(RESPONSE_BUCKETS, UDP_VOLUME)
        TCP_RESPONSE_SIZES_HIST = self.generate_request_hist(RESPONSE_BUCKETS, TCP_VOLUME)

        traffic_sizes = {
            "udp-request-sizes": UDP_REQUEST_SIZES_HIST,
            "udp-response-sizes": UDP_RESPONSE_SIZES_HIST,
            "tcp-request-sizes": TCP_REQUEST_SIZES_HIST,
            "tcp-response-sizes": TCP_RESPONSE_SIZES_HIST,
        }

        # Generate unique sources distribution
        if UDP_IPV4 + TCP_IPV4 == 1:
            NUM_SOURCES_IPV4 = 1
        else:
            NUM_SOURCES_IPV4 = random.randint(1, UDP_IPV4 + TCP_IPV4)

        if UDP_IPV6 + TCP_IPV6 == 1:
            NUM_SOURCES_IPV6 = 1
            NUM_SOURCES_IPV6_AGGREGATE = 1
        else:
            NUM_SOURCES_IPV6 = random.randint(1, UDP_IPV6 + TCP_IPV6)
            NUM_SOURCES_IPV6_AGGREGATE = random.randint(1, NUM_SOURCES_IPV6)

        unique_sources = {
            "num-sources-ipv4": NUM_SOURCES_IPV4,
            "num-sources-ipv6": NUM_SOURCES_IPV6,
            "num-sources-ipv6-aggregate": NUM_SOURCES_IPV6_AGGREGATE,
        }

        # Generate rcode-volume distribution
        RCODE_VOLUME = self.generate_rcode_volume(data_volume)
        rcode_volume = RCODE_VOLUME

        # Generate a list of rcode samples
        rcode_sample = self.hist_to_samples(RCODE_VOLUME)

        # Generate lists of ip_addresses
        ipv4_sample = self.generate_ipv4(NUM_SOURCES_IPV4, TCP_IPV4 + UDP_IPV4)
        ipv6_sample = self.generate_ipv6(NUM_SOURCES_IPV6, NUM_SOURCES_IPV6_AGGREGATE, TCP_IPV6 + UDP_IPV6)

        # Assign address lists to protocols
        udp_ipv4_src_addresses = ipv4_sample[:UDP_IPV4]
        ipv4_sample = ipv4_sample[UDP_IPV4:]

        udp_ipv6_src_addresses = ipv6_sample[:UDP_IPV6]
        ipv6_sample = ipv6_sample[UDP_IPV6:]

        tcp_ipv4_src_addresses = ipv4_sample[:TCP_IPV4]
        ipv4_sample = ipv4_sample[TCP_IPV4:]

        tcp_ipv6_src_addresses = ipv6_sample[:TCP_IPV6]
        ipv6_sample = ipv6_sample[TCP_IPV6:]

        # Put everything in big lists in order to zip afterwards
        src_address_list = [
            *udp_ipv4_src_addresses,
            *udp_ipv6_src_addresses,
            *tcp_ipv4_src_addresses,
            *tcp_ipv6_src_addresses,
        ]
        prot_list = [  # Protocol to IP address
            *([17] * UDP_VOLUME),
            *([6] * TCP_VOLUME),
        ]

        ip_version_list = [  # IP version to IP address, accounting for ordering
            *([4] * UDP_IPV4),
            *([6] * UDP_IPV6),
            *([4] * TCP_IPV4),
            *([6] * TCP_IPV6),
        ]

        # Generate request and response sizes
        request_sizes_list = [
            *self.hist_to_samples(UDP_REQUEST_SIZES_HIST),
            *self.hist_to_samples(TCP_REQUEST_SIZES_HIST),
        ]

        response_sizes_list = [
            *self.hist_to_samples(UDP_RESPONSE_SIZES_HIST),
            *self.hist_to_samples(TCP_RESPONSE_SIZES_HIST),
        ]

        time_list = [
            datetime.datetime(
                year=date.year,
                month=date.month,
                day=date.day,
                hour=random.randint(0, 23),
                minute=random.randint(0, 59),
                second=random.randint(0, 59),
                tzinfo=datetime.timezone.utc,
            ).astimezone()  # Save to database in local timezone.
            for _ in range(data_volume)
        ]

        return (
            zip(
                rcode_sample,
                time_list,
                prot_list,
                ip_version_list,
                request_sizes_list,
                response_sizes_list,
                src_address_list,
            ),
            traffic_volume,
            traffic_sizes,
            rcode_volume,
            unique_sources,
        )

    def get_expected_reports_with_service(self, service: str) -> dict[str, ServerData]:
        """
        Returns ground truth RSSAC002 distributions per server.
        """
        # empty string means it's the global report, hence no hyphen
        return {f"{service}-{key}" if key != "" else service: value for key, value in self.server_data.items()}

    def hist_to_samples(self, hist: dict[Any, int]) -> list[int]:
        """
        Creates random size samples, dictated by a dictionary.
        """
        res = []
        for key, value in hist.items():
            if isinstance(key, int):  # for rcode-volume
                res.extend([key] * value)
            if isinstance(key, str):  # for traffic-sizes
                split_bucket = key.split("-")
                lower = int(split_bucket[0])
                if len(split_bucket) > 1 and split_bucket[1] != "":
                    upper = int(split_bucket[1])
                    for _ in range(value):
                        if lower == 0:
                            lower += 1  # avoid length = 0
                        res.append(random.randint(lower, upper))
                else:
                    res.extend([lower] * value)

        random.shuffle(res)
        return res

    def generate_ipv4(self, num: int, total: int) -> list[str]:
        """
        Generates $total IPv4 address samples from a pool of $num unique IPv4 addresses.
        """
        unique_ips = [str(ipaddress.IPv4Address(random.getrandbits(32))) for _ in range(num)]
        if total > num and unique_ips:
            duplicate_ips = random.choices(unique_ips, k=total - num)
        else:
            duplicate_ips = []

        unique_ips.extend(duplicate_ips)
        return unique_ips

    def generate_ipv6(self, num_ipv6: int, num_subnets: int, total: int):
        """
        Generates $num_ipv6 IPv6 address samples from $num_ipv6 unique IPv6 addresses.
        Among the unique addresses there are exactly $num_64_prefixes unique /64 prefixes.
        """
        prefixes = [f"{self.get_64_bits()}" for _ in range(num_subnets)]
        addresses = []

        i = 0
        j = 0
        while i < num_ipv6:
            addresses.append(f"{prefixes[j]}:{self.get_64_bits()}")
            i += 1
            j = 0 if (j + 1) == len(prefixes) else j + 1

        if total > num_ipv6 and addresses:
            duplicate_ips = random.choices(addresses, k=total - num_ipv6)
        else:
            duplicate_ips = []

        addresses.extend(duplicate_ips)
        return addresses

    def get_64_bits(self) -> str:
        """Returns a 64-bit exploded portion of an IPv6 address."""
        return str(ipaddress.IPv6Address(random.getrandbits(64)).exploded)[20:]

    def generate_request_hist(self, buckets: set[str], num_samples: int) -> dict[str, int]:
        """
        Generates a random histogram, respecting the number of samples by
        randomly picking a bucket, then incrementing the corresponding value
            in the generated histogram.
        """
        hist = defaultdict(int)
        for _ in range(num_samples):
            bucket = random.choice(list(buckets))
            hist[bucket] += 1

        return hist

    def generate_rcode_volume(self, num_samples: int) -> dict[int, int]:
        """
        Generates a random rcode distribution, respecting the number of samples by
        randomly picking an rcode, then incrementing the rcode in the generated distribution.
        """
        rcode_volume = defaultdict(int)
        for _ in range(num_samples):
            rcode = random.randint(0, 10)
            rcode_volume[rcode] += 1

        return rcode_volume

    async def create_record(self, dns_rcode, time, prot, ip_version, dns_req_len, dns_res_len, ip_src, server) -> None:
        await self.query_executor.execute(
            fill_in_table(), (dns_rcode, time, prot, ip_version, dns_req_len, dns_res_len, ip_src, server)
        )
