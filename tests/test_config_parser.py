import os
import shutil
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytz

from src.config.config_parser import parse_config
from src.generators.ReportGenerator import ReportGenerator
from src.querying.query_executors import TrinoQueryExecutor

TEST_CONFIG_PATH = Path('./TEST_CONFIG_DIR/rssac002_config')

class ConfigParserTest(unittest.TestCase):

    def write_config(self, config_string: str):
        os.makedirs(TEST_CONFIG_PATH.parent)
        with open(TEST_CONFIG_PATH, 'w') as f:
            f.write(config_string)

    def test_example(self):
        self.write_config("""
        db_timezone: 'UTC'
        export_root: ./RSSAC002-data
        schedule: 
            type: fixed_window
            start_time: 2026-05-25T09:38:59+00:00
            window_start: 00:01
            window_end: 00:01
            generation_time: 03:01
        
        query_connection:
            engine: trino
            host: localhost
            port: 8085
            user: admin
            catalog: iceberg
            schema: entrada

        service_name: SIDN
        short_service: .nl
        per_ns_mode: true
        """)

        
        path, per_ns_mode, scheduler = parse_config(TEST_CONFIG_PATH)

        self.assertEqual(path, Path('./RSSAC002-data'))
        self.assertTrue(per_ns_mode)

        self.assertEqual(len(scheduler.pending_windows), 4)
        for gen, windows in scheduler.pending_windows.items():
            self.assertTrue(isinstance(gen, ReportGenerator))
            self.assertTrue(isinstance(gen.query_executor, TrinoQueryExecutor))
            self.assertEqual(gen.service_name, 'SIDN')
            self.assertEqual(gen.short_service, '.nl')

            self.assertListEqual(windows, [])

        schedule = scheduler.schedule

        self.assertEqual(schedule.db_timezone, pytz.timezone('UTC'))
        self.assertEqual(schedule.last_start, None)
        self.assertEqual(schedule.last_end, None)
        self.assertEqual(schedule.next_generation_time, 
                         datetime(year=2026, month=5, day=26, hour=3, minute=1, second=0, tzinfo=timezone.utc))
        self.assertEqual(schedule.next_window_start, 
                         datetime(year=2026, month=5, day=25, hour=0, minute=1, second=0, tzinfo=timezone.utc))
        self.assertEqual(schedule.next_window_end, 
                         datetime(year=2026, month=5, day=26, hour=0, minute=1, second=0, tzinfo=timezone.utc))
        
    def test_defaulting(self):
        self.write_config("""
        db_timezone: 'UTC'
        export_root: ./RSSAC002-data
        schedule: 
            type: fixed_window
            start_time: 2026-05-25T09:38:59+00:00
        
        query_connection:
            engine: trino
            host: localhost
            port: 8085
            user: admin
            catalog: iceberg
            schema: entrada

        service_name: SIDN
        short_service: .nl
        per_ns_mode: true
        """)
    
        path, per_ns_mode, scheduler = parse_config(TEST_CONFIG_PATH)


        self.assertEqual(path, Path('./RSSAC002-data'))
        self.assertTrue(per_ns_mode)

        self.assertEqual(len(scheduler.pending_windows), 4)
        for gen, windows in scheduler.pending_windows.items():
            self.assertTrue(isinstance(gen, ReportGenerator))
            self.assertTrue(isinstance(gen.query_executor, TrinoQueryExecutor))
            self.assertEqual(gen.service_name, 'SIDN')
            self.assertEqual(gen.short_service, '.nl')

            self.assertListEqual(windows, [])

        schedule = scheduler.schedule

        self.assertEqual(schedule.db_timezone, pytz.timezone('UTC'))
        self.assertEqual(schedule.last_start, None)
        self.assertEqual(schedule.last_end, None)
        self.assertEqual(schedule.next_generation_time, 
                         datetime(year=2026, month=5, day=26, hour=3, minute=0, second=0, tzinfo=timezone.utc))
        self.assertEqual(schedule.next_window_start, 
                         datetime(year=2026, month=5, day=25, hour=0, minute=0, second=0, tzinfo=timezone.utc))
        self.assertEqual(schedule.next_window_end, 
                         datetime(year=2026, month=5, day=26, hour=0, minute=0, second=0, tzinfo=timezone.utc))
        

    def test_no_tzinfo(self):
        self.write_config("""
        db_timezone: 'UTC'
        export_root: ./RSSAC002-data
        schedule: 
            type: fixed_window
            start_time: 2026-05-25T09:38:59
        
        query_connection:
            engine: trino
            host: localhost
            port: 8085
            user: admin
            catalog: iceberg
            schema: entrada

        service_name: SIDN
        short_service: .nl
        per_ns_mode: true
        """)
    
        path, per_ns_mode, scheduler = parse_config(TEST_CONFIG_PATH)


        self.assertEqual(path, Path('./RSSAC002-data'))
        self.assertTrue(per_ns_mode)

        self.assertEqual(len(scheduler.pending_windows), 4)
        for gen, windows in scheduler.pending_windows.items():
            self.assertTrue(isinstance(gen, ReportGenerator))
            self.assertTrue(isinstance(gen.query_executor, TrinoQueryExecutor))
            self.assertEqual(gen.service_name, 'SIDN')
            self.assertEqual(gen.short_service, '.nl')

            self.assertListEqual(windows, [])

        schedule = scheduler.schedule

        self.assertEqual(schedule.db_timezone, pytz.timezone('UTC'))
        self.assertEqual(schedule.last_start, None)
        self.assertEqual(schedule.last_end, None)
        self.assertEqual(schedule.next_generation_time, 
                         datetime(year=2026, month=5, day=26, hour=3, minute=0, second=0, tzinfo=timezone.utc))
        self.assertEqual(schedule.next_window_start, 
                         datetime(year=2026, month=5, day=25, hour=0, minute=0, second=0, tzinfo=timezone.utc))
        self.assertEqual(schedule.next_window_end, 
                         datetime(year=2026, month=5, day=26, hour=0, minute=0, second=0, tzinfo=timezone.utc))
        

    def test_start_time_defaulting(self):
        self.write_config("""
        db_timezone: 'UTC'
        export_root: ./RSSAC002-data
        schedule: 
            type: fixed_window
           
        query_connection:
            engine: trino
            host: localhost
            port: 8085
            user: admin
            catalog: iceberg
            schema: entrada

        service_name: SIDN
        short_service: .nl
        per_ns_mode: true
        """)
        
        with patch('src.scheduling.schedule.datetime.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(year=2026, month=5, day=25, hour=9, minute=38, second=59)
            path, per_ns_mode, scheduler = parse_config(TEST_CONFIG_PATH)


        self.assertEqual(path, Path('./RSSAC002-data'))
        self.assertTrue(per_ns_mode)

        self.assertEqual(len(scheduler.pending_windows), 4)
        for gen, windows in scheduler.pending_windows.items():
            self.assertTrue(isinstance(gen, ReportGenerator))
            self.assertTrue(isinstance(gen.query_executor, TrinoQueryExecutor))
            self.assertEqual(gen.service_name, 'SIDN')
            self.assertEqual(gen.short_service, '.nl')

            self.assertListEqual(windows, [])

        schedule = scheduler.schedule

        self.assertEqual(schedule.db_timezone, pytz.timezone('UTC'))
        self.assertEqual(schedule.last_start, None)
        self.assertEqual(schedule.last_end, None)
        self.assertEqual(schedule.next_generation_time, 
                         datetime(year=2026, month=5, day=26, hour=3, minute=0, second=0, tzinfo=timezone.utc))
        self.assertEqual(schedule.next_window_start, 
                         datetime(year=2026, month=5, day=25, hour=0, minute=0, second=0, tzinfo=timezone.utc))
        self.assertEqual(schedule.next_window_end, 
                         datetime(year=2026, month=5, day=26, hour=0, minute=0, second=0, tzinfo=timezone.utc))
        
    def test_invalid_timezone(self):
        self.write_config("""
        db_timezone: 'invalid'
        export_root: ./RSSAC002-data
        schedule: 
            type: fixed_window
        
        query_connection:
            engine: trino
            host: localhost
            port: 8085
            user: admin
            catalog: iceberg
            schema: entrada

        service_name: SIDN
        short_service: .nl
        per_ns_mode: true
        """)

        with self.assertRaises(ValueError):
            path, per_ns_mode, scheduler = parse_config(TEST_CONFIG_PATH)

        
    def tearDown(self):
        if os.path.exists(TEST_CONFIG_PATH.parent):
            shutil.rmtree(TEST_CONFIG_PATH.parent)
