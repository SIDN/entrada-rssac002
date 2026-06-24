import datetime
import os
import random
import shutil
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import yaml
from loguru import logger

from src.customexceptions import PermanentError, TransientError
from src.exporting.report_exporting import ExportClosure, ReportExporter
from src.reports.histogramutils import REQUEST_BUCKETS, RESPONSE_BUCKETS
from src.reports.reports import RCodeVolumeReport, Report, TrafficSizesReport, TrafficVolumeReport, UniqueSourcesReport

TEST_ROOT = Path("RSSAC002-test-data")
RANDOM_LOWER = 0
RANDOM_UPPER = 1000
RCODE_MIN = 0
RCODE_MAX = 4095
SHORT_SERVICE = "short_name"

kwargs = {
    "version": "rssac002v5",
    "service": "service",
    "start_period": datetime.datetime(
        year=2000, month=1, day=1, hour=0, minute=0, second=0, tzinfo=datetime.timezone.utc
    ),
}

xp_metadata = {
    "version": "rssac002v5",
    "service": "service",
    "start-period": datetime.datetime(
        year=2000, month=1, day=1, hour=0, minute=0, second=0, tzinfo=datetime.timezone.utc
    ).isoformat(),
}

DUMMY_REPORT = RCodeVolumeReport(
    short_service="short_service",
    version="version",
    service="service",
    start_period=datetime.datetime(year=2000, month=1, day=1, hour=0, minute=0, second=0, tzinfo=datetime.timezone.utc),
    rcode_volume={},
)


def hyphen_keys(dictionary: dict[str, Any]) -> dict[str, Any]:
    return {key.replace("_", "-"): value for key, value in dictionary.items()}


class ExportingTests(unittest.TestCase):
    def setUp(self):
        logger.remove()

    def assertions(self, xp_path_report_dict: list[(str, Report, dict)]) -> None:
        for (xp_path, report, xp_dict) in xp_path_report_dict:
            metric = report.metric

            self.assertFalse(os.path.exists(xp_path))

            e = ReportExporter()
            e.export_reports([report], TEST_ROOT)

            self.assertTrue(os.path.exists(xp_path))
            
            with open(xp_path, "r") as f:
                saved = yaml.safe_load(f)

            full_xp_dict = xp_metadata | {"metric": metric} | xp_dict
            self.assertDictEqual(full_xp_dict, saved)

    def test_single_traffic_volume(self):
        """Test single report exporting for traffic volume"""
        args = {
            "dns_udp_queries_received_ipv4": random.randint(RANDOM_LOWER, RANDOM_UPPER),
            "dns_udp_queries_received_ipv6": random.randint(RANDOM_LOWER, RANDOM_UPPER),
            "dns_tcp_queries_received_ipv4": random.randint(RANDOM_LOWER, RANDOM_UPPER),
            "dns_tcp_queries_received_ipv6": random.randint(RANDOM_LOWER, RANDOM_UPPER),
            "dns_udp_responses_sent_ipv4": random.randint(RANDOM_LOWER, RANDOM_UPPER),
            "dns_udp_responses_sent_ipv6": random.randint(RANDOM_LOWER, RANDOM_UPPER),
            "dns_tcp_responses_sent_ipv4": random.randint(RANDOM_LOWER, RANDOM_UPPER),
            "dns_tcp_responses_sent_ipv6": random.randint(RANDOM_LOWER, RANDOM_UPPER),
        }
        
        xp_path = fr'{TEST_ROOT}/2000/01/traffic-volume/short_name-20000101-traffic-volume.yaml'
        xp_dict = xp_metadata | hyphen_keys(args)
        r = [(xp_path, TrafficVolumeReport(short_service=SHORT_SERVICE, **kwargs, **args), xp_dict)]
        self.assertions(r)

    def test_single_traffic_sizes(self):
        args = {
            "udp_request_sizes": {key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in REQUEST_BUCKETS},
            "udp_response_sizes": {key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in RESPONSE_BUCKETS},
            "tcp_request_sizes": {key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in REQUEST_BUCKETS},
            "tcp_response_sizes": {key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in RESPONSE_BUCKETS},
        }

        xp_args = {}
        for stat in args:
            xp_args[stat] = {key: value for key, value in args[stat].items() if value > 0}

        xp_path = fr'{TEST_ROOT}/2000/01/traffic-sizes/short_name-20000101-traffic-sizes.yaml'
        xp_dict = xp_metadata | hyphen_keys(xp_args)
        r = [(xp_path, TrafficSizesReport(short_service=SHORT_SERVICE, **kwargs, **args), xp_dict)]
        self.assertions(r)

    def test_single_rcode_volume(self):
        rcode_volume = {
            rcode: random.randint(RANDOM_LOWER, RANDOM_UPPER) for rcode in sorted(random.sample(range(100), 20))
        }

        xp_args = {key: value for key, value in rcode_volume.items() if value > 0}
        xp_dict = xp_metadata | xp_args

        xp_path = fr'{TEST_ROOT}/2000/01/rcode-volume/short_name-20000101-rcode-volume.yaml'
       
        r = [(xp_path, RCodeVolumeReport(short_service=SHORT_SERVICE, **kwargs, rcode_volume=rcode_volume), xp_dict)]
        self.assertions(r)

    def test_unique_sources_exporting(self):
        args = {
            "num_sources_ipv4": random.randint(RANDOM_LOWER, RANDOM_UPPER),
            "num_sources_ipv6": random.randint(RANDOM_LOWER, RANDOM_UPPER),
            "num_sources_ipv6_aggregate": random.randint(RANDOM_LOWER, RANDOM_UPPER),
        }
        xp_args = {key: value for key, value in args.items() if value > 0}

        xp_dict = xp_metadata | hyphen_keys(xp_args)
        xp_path = fr'{TEST_ROOT}/2000/01/unique-sources/short_name-20000101-unique-sources.yaml'
        
        r = [(xp_path, UniqueSourcesReport(short_service=SHORT_SERVICE, **kwargs, **args), xp_dict)]
        self.assertions(r)

    def test_export_all(self):
        r = []
        #traffic-volume
        args = {
            "dns_udp_queries_received_ipv4": random.randint(RANDOM_LOWER, RANDOM_UPPER),
            "dns_udp_queries_received_ipv6": random.randint(RANDOM_LOWER, RANDOM_UPPER),
            "dns_tcp_queries_received_ipv4": random.randint(RANDOM_LOWER, RANDOM_UPPER),
            "dns_tcp_queries_received_ipv6": random.randint(RANDOM_LOWER, RANDOM_UPPER),
            "dns_udp_responses_sent_ipv4": random.randint(RANDOM_LOWER, RANDOM_UPPER),
            "dns_udp_responses_sent_ipv6": random.randint(RANDOM_LOWER, RANDOM_UPPER),
            "dns_tcp_responses_sent_ipv4": random.randint(RANDOM_LOWER, RANDOM_UPPER),
            "dns_tcp_responses_sent_ipv6": random.randint(RANDOM_LOWER, RANDOM_UPPER),
        }
        
        xp_path = fr'{TEST_ROOT}/2000/01/traffic-volume/short_name-20000101-traffic-volume.yaml'
        xp_dict = xp_metadata | hyphen_keys(args)
        r.append((xp_path, TrafficVolumeReport(short_service=SHORT_SERVICE, **kwargs, **args), xp_dict))

        #traffic-sizes
        args = {
            "udp_request_sizes": {key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in REQUEST_BUCKETS},
            "udp_response_sizes": {key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in RESPONSE_BUCKETS},
            "tcp_request_sizes": {key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in REQUEST_BUCKETS},
            "tcp_response_sizes": {key: random.randint(RANDOM_LOWER, RANDOM_UPPER) for key in RESPONSE_BUCKETS},
        }

        xp_args = {}
        for stat in args:
            xp_args[stat] = {key: value for key, value in args[stat].items() if value > 0}

        xp_path = fr'{TEST_ROOT}/2000/01/traffic-sizes/short_name-20000101-traffic-sizes.yaml'
        xp_dict = xp_metadata | hyphen_keys(xp_args)
        r.append((xp_path, TrafficSizesReport(short_service=SHORT_SERVICE, **kwargs, **args), xp_dict))
        
        #rcode-volume
        rcode_volume = {
            rcode: random.randint(RANDOM_LOWER, RANDOM_UPPER) for rcode in sorted(random.sample(range(100), 20))
        }

        xp_args = {key: value for key, value in rcode_volume.items() if value > 0}
        xp_dict = xp_metadata | xp_args

        xp_path = fr'{TEST_ROOT}/2000/01/rcode-volume/short_name-20000101-rcode-volume.yaml'
       
        r.append(
            (xp_path, RCodeVolumeReport(short_service=SHORT_SERVICE, **kwargs, rcode_volume=rcode_volume), xp_dict)
        )

        #unique-sources
        args = {
            "num_sources_ipv4": random.randint(RANDOM_LOWER, RANDOM_UPPER),
            "num_sources_ipv6": random.randint(RANDOM_LOWER, RANDOM_UPPER),
            "num_sources_ipv6_aggregate": random.randint(RANDOM_LOWER, RANDOM_UPPER),
        }
        xp_args = {key: value for key, value in args.items() if value > 0}

        xp_dict = xp_metadata | hyphen_keys(xp_args)
        xp_path = fr'{TEST_ROOT}/2000/01/unique-sources/short_name-20000101-unique-sources.yaml'
        
        r.append((xp_path, UniqueSourcesReport(short_service=SHORT_SERVICE, **kwargs, **args), xp_dict))

        #final assertion
        self.assertions(r)

    def test_extend_report_queue(self):
        """Tests correctness of closures within the export queue"""
        e = ReportExporter()
        self.assertListEqual(e.export_queue, [])
        
        reports = [
            a := TrafficSizesReport(short_service=SHORT_SERVICE, **kwargs), 
            b := TrafficVolumeReport(short_service=SHORT_SERVICE, **kwargs),
            c := RCodeVolumeReport(short_service=SHORT_SERVICE, **kwargs),
            d := UniqueSourcesReport(short_service=SHORT_SERVICE, **kwargs),
        ]

        e.extend_export_queue(reports, TEST_ROOT)

        xp_closures = [
            ExportClosure(a, TEST_ROOT),
            ExportClosure(b, TEST_ROOT),
            ExportClosure(c, TEST_ROOT),
            ExportClosure(d, TEST_ROOT),
        ]

        self.assertListEqual(xp_closures, e.export_queue)

        reports2 = [
            a2 := TrafficSizesReport(short_service=SHORT_SERVICE, **kwargs), 
            b2 := TrafficVolumeReport(short_service=SHORT_SERVICE, **kwargs),
            c2 := RCodeVolumeReport(short_service=SHORT_SERVICE, **kwargs),
            d2 := UniqueSourcesReport(short_service=SHORT_SERVICE, **kwargs),
        ]

        e.extend_export_queue(reports2, f'{TEST_ROOT}2')

        xp_closures2 = [
            ExportClosure(a, TEST_ROOT),
            ExportClosure(b, TEST_ROOT),
            ExportClosure(c, TEST_ROOT),
            ExportClosure(d, TEST_ROOT),
            ExportClosure(a2, f'{TEST_ROOT}2'),
            ExportClosure(b2, f'{TEST_ROOT}2'),
            ExportClosure(c2, f'{TEST_ROOT}2'),
            ExportClosure(d2, f'{TEST_ROOT}2'),
        ]

        self.assertListEqual(xp_closures2, e.export_queue)

    def test_export_report(self):
        
        a = TrafficSizesReport(short_service=SHORT_SERVICE, **kwargs)
        b = TrafficVolumeReport(short_service=SHORT_SERVICE, **kwargs)
        c = RCodeVolumeReport(short_service=SHORT_SERVICE, **kwargs)
        d = UniqueSourcesReport(short_service=SHORT_SERVICE, **kwargs)
        
        c1 = ExportClosure(a, TEST_ROOT)
        c2 = ExportClosure(b, TEST_ROOT)
        c3 = ExportClosure(c, TEST_ROOT)
        c4 = ExportClosure(d, TEST_ROOT)

        c1path = fr'{TEST_ROOT}/2000/01/traffic-sizes/short_name-20000101-traffic-sizes.yaml'
        c2path = fr'{TEST_ROOT}/2000/01/traffic-volume/short_name-20000101-traffic-volume.yaml'
        c3path = fr'{TEST_ROOT}/2000/01/rcode-volume/short_name-20000101-rcode-volume.yaml'
        c4path = fr'{TEST_ROOT}/2000/01/unique-sources/short_name-20000101-unique-sources.yaml'


        e = ReportExporter()

        #Test separate exporting...
        e.export_report(c1)
        self.assertTrue(os.path.exists(c1path))

        e.export_report(c2)
        self.assertTrue(os.path.exists(c2path))

        e.export_report(c3)
        self.assertTrue(os.path.exists(c3path))

        e.export_report(c4)
        self.assertTrue(os.path.exists(c4path))

        #...and check if they don't overwrite each other.
        self.assertTrue(os.path.exists(c1path))
        self.assertTrue(os.path.exists(c2path))
        self.assertTrue(os.path.exists(c3path))
        self.assertTrue(os.path.exists(c4path))

    def test_transient_handling(self):
        reports = [a := TrafficSizesReport(short_service=SHORT_SERVICE, **kwargs),
                        RCodeVolumeReport(short_service=SHORT_SERVICE, **kwargs)]
        
        def raise_on_specific(closure: ExportClosure):
            if closure.report == a:
                raise TransientError("transient")


        with patch.object(ReportExporter, 'export_report', side_effect=raise_on_specific):
            e = ReportExporter()
            e.export_reports(reports, TEST_ROOT)
            self.assertListEqual(e.export_queue, [ExportClosure(a, TEST_ROOT)])

        e.export_reports([], TEST_ROOT)
        self.assertListEqual(e.export_queue, [])

    def test_permanent_handling(self):
        reports = [a := TrafficSizesReport(short_service=SHORT_SERVICE, **kwargs),
                        RCodeVolumeReport(short_service=SHORT_SERVICE, **kwargs)]
        
        def raise_on_specific(closure: ExportClosure):
            if closure.report == a:
                raise PermanentError("permanent")


        with patch.object(ReportExporter, 'export_report', side_effect=raise_on_specific):
            e = ReportExporter()
            with self.assertRaises(PermanentError):
                e.export_reports(reports, TEST_ROOT)
            
    def test_file_exists_error(self):
        e = ReportExporter()
        with (
            patch("src.exporting.report_exporting.os.makedirs") as mock_mkdirs
        ):
            mock_mkdirs.side_effect = FileExistsError
            with self.assertRaises(PermanentError):
                e.export_report(ExportClosure(DUMMY_REPORT, TEST_ROOT))
            

    def test_fnf_error(self):
        e = ReportExporter()
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = FileNotFoundError
            with self.assertRaises(TransientError):
                e.export_report(ExportClosure(DUMMY_REPORT, TEST_ROOT))

    def test_permission_error(self):
        e = ReportExporter()
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = PermissionError
            with self.assertRaises(TransientError):
                e.export_report(ExportClosure(DUMMY_REPORT, TEST_ROOT))

    def test_io_error(self):
        e = ReportExporter()
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = IOError
            with self.assertRaises(TransientError):
                e.export_report(ExportClosure(DUMMY_REPORT, TEST_ROOT))

    def test_os_error(self):
        e = ReportExporter()
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = OSError
            with self.assertRaises(TransientError):
                e.export_report(ExportClosure(DUMMY_REPORT, TEST_ROOT))

    def test_yaml_error(self):
        e = ReportExporter()
        with (
            patch("src.exporting.report_exporting.yaml.dump_all") as mock_dump_all
        ):
            mock_dump_all.side_effect = yaml.YAMLError
            with self.assertRaises(PermanentError):
                e.export_report(ExportClosure(DUMMY_REPORT, TEST_ROOT))

    def test_os_os_error(self):
        e = ReportExporter()
        with (
            patch("src.exporting.report_exporting.os.makedirs") as mock_mkdirs
        ):
            mock_mkdirs.side_effect = OSError
            with self.assertRaises(TransientError):
                e.export_report(ExportClosure(DUMMY_REPORT, TEST_ROOT))


    def tearDown(self):
        if os.path.exists(TEST_ROOT):
            shutil.rmtree(TEST_ROOT)


if __name__ == "__main__":
    unittest.main()
