import argparse
import datetime
from pathlib import Path

from src.exporting.report_exporting import ExportClosure


def parse_date(value: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid date: {value!r}; expected YYYY-MM-DD") from exc


def daily_windows(
    start_date: datetime.date,
    end_date: datetime.date,
    database_timezone,
) -> list[tuple[datetime.datetime, datetime.datetime]]:
    """Return daily windows in the configured database timezone.

    Each window is inclusive of its start and exclusive of its end, matching the
    time filters used in the query catalog.
    """
    windows: list[tuple[datetime.datetime, datetime.datetime]] = []
    cursor = datetime.datetime.combine(start_date, datetime.time.min, tzinfo=database_timezone)
    end_marker = datetime.datetime.combine(end_date + datetime.timedelta(days=1), datetime.time.min, tzinfo=database_timezone)

    while cursor < end_marker:
        next_window = cursor + datetime.timedelta(days=1)
        windows.append((cursor, next_window))
        cursor = next_window

    return windows


def make_export_closure(report, base_path: Path | str, overwrite_existing: bool = False) -> ExportClosure:
    return ExportClosure(report=report, base_path=Path(base_path), overwrite_existing=overwrite_existing)
