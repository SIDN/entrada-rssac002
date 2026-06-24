import asyncio
import unittest
from unittest.mock import patch

from loguru import logger

from src.customexceptions import PermanentError
from src.main import Orchestrator


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

