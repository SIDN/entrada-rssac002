import datetime as dt
import random
import unittest
from pathlib import Path

from src.customexceptions import InvalidReportError
from src.reports.histogramutils import REQUEST_BUCKETS, RESPONSE_BUCKETS
from src.reports.reports import (
    RCodeVolumeReport,
    TrafficSizesReport,
    TrafficVolumeReport,
    UniqueSourcesReport,
    sum_dictionaries,
)

RANDOM_LOWER = 1
RANDOM_UPPER = 10000

RCODE_MIN = 0
RCODE_MAX = 4095

SHORT_SERVICE = "short_service"
VERSION = "rssac002v5"
SERVICE = "Operator"
START_PERIOD = dt.datetime(day=8, month=6, year=2026, hour=0, minute=0, second=0, tzinfo=dt.timezone.utc)


class ReportTests(unittest.TestCase):
    def test_traffic_volume_valid(self):
        """Test correct input for traffic volume"""
        dns_udp_queries_received_ipv4 = random.randint(RANDOM_LOWER, RANDOM_UPPER)
        dns_udp_queries_received_ipv6 = random.randint(RANDOM_LOWER, RANDOM_UPPER)
        dns_tcp_queries_received_ipv4 = random.randint(RANDOM_LOWER, RANDOM_UPPER)
        dns_tcp_queries_received_ipv6 = random.randint(RANDOM_LOWER, RANDOM_UPPER)
        dns_udp_responses_sent_ipv4 = random.randint(RANDOM_LOWER, RANDOM_UPPER)
        dns_udp_responses_sent_ipv6 = random.randint(RANDOM_LOWER, RANDOM_UPPER)
        dns_tcp_responses_sent_ipv4 = random.randint(RANDOM_LOWER, RANDOM_UPPER)
        dns_tcp_responses_sent_ipv6 = random.randint(RANDOM_LOWER, RANDOM_UPPER)

        r = TrafficVolumeReport(
            short_service=SHORT_SERVICE,
            version=VERSION,
            service=SERVICE,
            start_period=START_PERIOD,
            dns_udp_queries_received_ipv4=dns_udp_queries_received_ipv4,
            dns_udp_queries_received_ipv6=dns_udp_queries_received_ipv6,
            dns_tcp_queries_received_ipv4=dns_tcp_queries_received_ipv4,
            dns_tcp_queries_received_ipv6=dns_tcp_queries_received_ipv6,
            dns_udp_responses_sent_ipv4=dns_udp_responses_sent_ipv4,
            dns_udp_responses_sent_ipv6=dns_udp_responses_sent_ipv6,
            dns_tcp_responses_sent_ipv4=dns_tcp_responses_sent_ipv4,
            dns_tcp_responses_sent_ipv6=dns_tcp_responses_sent_ipv6,
        )

        xp_dict = {
            "version": VERSION,
            "service": SERVICE,
            "metric": "traffic-volume",
            "start-period": START_PERIOD.isoformat(),
            "dns-udp-queries-received-ipv4": dns_udp_queries_received_ipv4,
            "dns-udp-queries-received-ipv6": dns_udp_queries_received_ipv6,
            "dns-tcp-queries-received-ipv4": dns_tcp_queries_received_ipv4,
            "dns-tcp-queries-received-ipv6": dns_tcp_queries_received_ipv6,
            "dns-udp-responses-sent-ipv4": dns_udp_responses_sent_ipv4,
            "dns-udp-responses-sent-ipv6": dns_udp_responses_sent_ipv6,
            "dns-tcp-responses-sent-ipv4": dns_tcp_responses_sent_ipv4,
            "dns-tcp-responses-sent-ipv6": dns_tcp_responses_sent_ipv6,
        }

        xp_path = Path("2026/06/traffic-volume")
        self.assertEqual(xp_path, r.export_loc)
        xp_filename = "short_service-20260608-traffic-volume.yaml"
        self.assertEqual(xp_filename, r.filename)

        self.assertDictEqual(r.to_dict(), xp_dict)

    def test_traffic_sizes_valid(self):
        udp_request_sizes = {key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in REQUEST_BUCKETS}
        udp_response_sizes = {key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in RESPONSE_BUCKETS}
        tcp_request_sizes = {key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in REQUEST_BUCKETS}
        tcp_response_sizes = {key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in RESPONSE_BUCKETS}

        r = TrafficSizesReport(
            short_service=SHORT_SERVICE,
            version=VERSION,
            service=SERVICE,
            start_period=START_PERIOD,
            udp_request_sizes=udp_request_sizes,
            udp_response_sizes=udp_response_sizes,
            tcp_request_sizes=tcp_request_sizes,
            tcp_response_sizes=tcp_response_sizes,
        )

        xp_dict = {
            "version": VERSION,
            "service": SERVICE,
            "start-period": START_PERIOD.isoformat(),
            "metric": "traffic-sizes",
            "udp-request-sizes": udp_request_sizes,
            "udp-response-sizes": udp_response_sizes,
            "tcp-request-sizes": tcp_request_sizes,
            "tcp-response-sizes": tcp_response_sizes,
        }

        xp_path = Path("2026/06/traffic-sizes")
        self.assertEqual(xp_path, r.export_loc)
        xp_filename = "short_service-20260608-traffic-sizes.yaml"
        self.assertEqual(xp_filename, r.filename)

        self.assertDictEqual(xp_dict, r.to_dict())

    def test_rcode_volume_valid(self):
        rcode_volume = {rcode: random.randint(RANDOM_LOWER, RANDOM_UPPER) for rcode in random.sample(range(100), 20)}

        r = RCodeVolumeReport(
            short_service=SHORT_SERVICE,
            version=VERSION,
            service=SERVICE,
            start_period=START_PERIOD,
            rcode_volume=rcode_volume,
        )

        xp_dict = {
            "version": VERSION,
            "service": SERVICE,
            "start-period": START_PERIOD.isoformat(),
            "metric": "rcode-volume",
        } | rcode_volume

        xp_path = Path("2026/06/rcode-volume")
        self.assertEqual(xp_path, r.export_loc)
        xp_filename = "short_service-20260608-rcode-volume.yaml"
        self.assertEqual(xp_filename, r.filename)

        self.assertDictEqual(rcode_volume, r.rcode_volume)
        self.assertDictEqual(xp_dict, r.to_dict())

    def test_unique_sources_valid(self):
        num_sources_ipv4 = random.randint(RANDOM_LOWER, RANDOM_UPPER)
        num_sources_ipv6 = random.randint(RANDOM_LOWER, RANDOM_UPPER)
        num_sources_ipv6_aggregate = random.randint(RANDOM_LOWER, RANDOM_UPPER)

        r = UniqueSourcesReport(
            short_service=SHORT_SERVICE,
            version=VERSION,
            service=SERVICE,
            start_period=START_PERIOD,
            num_sources_ipv4=num_sources_ipv4,
            num_sources_ipv6=num_sources_ipv6,
            num_sources_ipv6_aggregate=num_sources_ipv6_aggregate,
        )

        self.assertEqual(num_sources_ipv4, r.num_sources_ipv4)
        self.assertEqual(num_sources_ipv6, r.num_sources_ipv6)
        self.assertEqual(num_sources_ipv6_aggregate, r.num_sources_ipv6_aggregate)

        xp_dict = {
            "version": VERSION,
            "service": SERVICE,
            "metric": "unique-sources",
            "start-period": START_PERIOD.isoformat(),
            "num-sources-ipv4": num_sources_ipv4,
            "num-sources-ipv6": num_sources_ipv6,
            "num-sources-ipv6-aggregate": num_sources_ipv6_aggregate,
        }

        xp_path = Path("2026/06/unique-sources")
        self.assertEqual(xp_path, r.export_loc)
        xp_filename = "short_service-20260608-unique-sources.yaml"
        self.assertEqual(xp_filename, r.filename)

        self.assertDictEqual(xp_dict, r.to_dict())


    """
    Invalid arguments test:
    """
    def test_traffic_volume_invalid_negative(self):
        with self.assertRaises(InvalidReportError):
            TrafficVolumeReport(
                short_service=SHORT_SERVICE,
                version=VERSION,
                service=SERVICE,
                start_period=START_PERIOD,
                dns_udp_queries_received_ipv4=random.randint(RANDOM_LOWER, RANDOM_UPPER),
                dns_udp_queries_received_ipv6=random.randint(RANDOM_LOWER, RANDOM_UPPER),
                dns_tcp_queries_received_ipv4=random.randint(RANDOM_LOWER, RANDOM_UPPER),
                dns_tcp_queries_received_ipv6=-1,
                dns_udp_responses_sent_ipv4=random.randint(RANDOM_LOWER, RANDOM_UPPER),
                dns_udp_responses_sent_ipv6=random.randint(RANDOM_LOWER, RANDOM_UPPER),
                dns_tcp_responses_sent_ipv4=random.randint(RANDOM_LOWER, RANDOM_UPPER),
                dns_tcp_responses_sent_ipv6=random.randint(RANDOM_LOWER, RANDOM_UPPER),
            )
    
    def test_traffic_volume_invalid_non_integer(self):
        with self.assertRaises(InvalidReportError):
            TrafficVolumeReport(
                short_service=SHORT_SERVICE,
                version=VERSION,
                service=SERVICE,
                start_period=START_PERIOD,
                dns_udp_queries_received_ipv4=random.randint(RANDOM_LOWER, RANDOM_UPPER),
                dns_udp_queries_received_ipv6=random.randint(RANDOM_LOWER, RANDOM_UPPER),
                dns_tcp_queries_received_ipv4=random.randint(RANDOM_LOWER, RANDOM_UPPER),
                dns_tcp_queries_received_ipv6=random.randint(RANDOM_LOWER, RANDOM_UPPER),
                dns_udp_responses_sent_ipv4=random.randint(RANDOM_LOWER, RANDOM_UPPER),
                dns_udp_responses_sent_ipv6=random.randint(RANDOM_LOWER, RANDOM_UPPER),
                dns_tcp_responses_sent_ipv4=random.randint(RANDOM_LOWER, RANDOM_UPPER),
                dns_tcp_responses_sent_ipv6='non integer value',
            )

    def test_traffic_sizes_invalid_negative(self):
        with self.assertRaises(InvalidReportError):
            TrafficSizesReport(
                short_service=SHORT_SERVICE,
                version=VERSION,
                service=SERVICE,
                start_period=START_PERIOD,
                udp_request_sizes={key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in REQUEST_BUCKETS},
                udp_response_sizes={key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in RESPONSE_BUCKETS},
                tcp_request_sizes=
                {key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in REQUEST_BUCKETS}| {'0-15': -1},
                tcp_response_sizes={key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in RESPONSE_BUCKETS},
            )

    def test_traffic_sizes_invalid_non_integer(self):
        with self.assertRaises(InvalidReportError):
            TrafficSizesReport(
                short_service=SHORT_SERVICE,
                version=VERSION,
                service=SERVICE,
                start_period=START_PERIOD,
                udp_request_sizes=
                {key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in REQUEST_BUCKETS} |  {'0-15': 'non-integer'},
                udp_response_sizes={key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in RESPONSE_BUCKETS},
                tcp_request_sizes={key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in REQUEST_BUCKETS},
                tcp_response_sizes={key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in RESPONSE_BUCKETS},
            )

    def test_traffic_sizes_invalid_non_dict(self):
        with self.assertRaises(InvalidReportError):
            TrafficSizesReport(
                short_service=SHORT_SERVICE,
                version=VERSION,
                service=SERVICE,
                start_period=START_PERIOD,
                udp_request_sizes=5,
                udp_response_sizes={key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in RESPONSE_BUCKETS},
                tcp_request_sizes={key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in REQUEST_BUCKETS},
                tcp_response_sizes={key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in RESPONSE_BUCKETS},
            )

    def test_traffic_sizes_invalid_unknown_bucket(self):
        with self.assertRaises(InvalidReportError):
            TrafficSizesReport(
                short_service=SHORT_SERVICE,
                version=VERSION,
                service=SERVICE,
                start_period=START_PERIOD,
                udp_request_sizes=
                {key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in REQUEST_BUCKETS} |  {'0-122': 5},
                udp_response_sizes={key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in RESPONSE_BUCKETS},
                tcp_request_sizes={key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in REQUEST_BUCKETS},
                tcp_response_sizes={key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in RESPONSE_BUCKETS},
            )

        
    def test_rcode_volume_invalid_non_integer_key(self):
        rcode_volume = {
            rcode: random.randint(RANDOM_LOWER, RANDOM_UPPER) for rcode in random.sample(range(100), 20)
        } | {'non-integer': 2}
        with self.assertRaises(InvalidReportError):
            RCodeVolumeReport(
                short_service=SHORT_SERVICE,
                version=VERSION,
                service=SERVICE,
                start_period=START_PERIOD,
                rcode_volume=rcode_volume,
            )

    def test_rcode_volume_invalid_non_dict(self):
        rcode_volume = 1
        with self.assertRaises(InvalidReportError):
            RCodeVolumeReport(
                short_service=SHORT_SERVICE,
                version=VERSION,
                service=SERVICE,
                start_period=START_PERIOD,
                rcode_volume=rcode_volume,
            )

    def test_rcode_volume_invalid_non_integer_value(self):
        rcode_volume = {
            rcode: random.randint(RANDOM_LOWER, RANDOM_UPPER) for rcode in random.sample(range(100), 20)
        } | {1: 'non-integer'}
        with self.assertRaises(InvalidReportError):
            RCodeVolumeReport(
                short_service=SHORT_SERVICE,
                version=VERSION,
                service=SERVICE,
                start_period=START_PERIOD,
                rcode_volume=rcode_volume,
            )

    def test_rcode_volume_invalid_negative_value(self):
        rcode_volume = {
            rcode: random.randint(RANDOM_LOWER, RANDOM_UPPER) for rcode in random.sample(range(100), 20)
        } | {1: -1}
        with self.assertRaises(InvalidReportError):
            RCodeVolumeReport(
                short_service=SHORT_SERVICE,
                version=VERSION,
                service=SERVICE,
                start_period=START_PERIOD,
                rcode_volume=rcode_volume,
            )

    def test_rcode_volume_invalid_key_out_of_range(self):
        rcode_volume = {
            rcode: random.randint(RANDOM_LOWER, RANDOM_UPPER) for rcode in random.sample(range(100), 20)
        } | {4096: 1}
        with self.assertRaises(InvalidReportError):
            RCodeVolumeReport(
                short_service=SHORT_SERVICE,
                version=VERSION,
                service=SERVICE,
                start_period=START_PERIOD,
                rcode_volume=rcode_volume,
            )

    def test_unique_sources_invalid_non_integer(self):
        num_sources_ipv4 = random.randint(RANDOM_LOWER, RANDOM_UPPER)
        num_sources_ipv6 = 'non-integer'
        num_sources_ipv6_aggregate = random.randint(RANDOM_LOWER, RANDOM_UPPER)

        with self.assertRaises(InvalidReportError):
            UniqueSourcesReport(
                short_service=SHORT_SERVICE,
                version=VERSION,
                service=SERVICE,
                start_period=START_PERIOD,
                num_sources_ipv4=num_sources_ipv4,
                num_sources_ipv6=num_sources_ipv6,
                num_sources_ipv6_aggregate=num_sources_ipv6_aggregate,
            )


    def test_unique_sources_invalid_negative_value(self):
        num_sources_ipv4 = -1
        num_sources_ipv6 = random.randint(RANDOM_LOWER, RANDOM_UPPER)
        num_sources_ipv6_aggregate = random.randint(RANDOM_LOWER, RANDOM_UPPER)
        
        with self.assertRaises(InvalidReportError):
            UniqueSourcesReport(
                short_service=SHORT_SERVICE,
                version=VERSION,
                service=SERVICE,
                start_period=START_PERIOD,
                num_sources_ipv4=num_sources_ipv4,
                num_sources_ipv6=num_sources_ipv6,
                num_sources_ipv6_aggregate=num_sources_ipv6_aggregate,
            )

    def test_sum_dictionaries(self):
        dict_1 = {'a': 1, 'c': {'a': 1, 'b': 2}, 'e': {'q': 8}}
        
        dict_2 = {'a': 2, 'b': 3, 'c': {'a': 2, 'c':1}, 'd': {'aa': 3, 'bb': 4, 'cc': 4}}

        xp = {'a': 3, 'b': 3, 'c': {'a': 3, 'b': 2, 'c': 1}, 'd': {'aa': 3, 'bb': 4, 'cc': 4}, 'e': {'q': 8}}
        self.assertDictEqual(sum_dictionaries(dict_1, dict_2), xp)

    if __name__ == "__main__":
        unittest.main()
