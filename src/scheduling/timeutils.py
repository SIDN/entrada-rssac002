import datetime

from src.customexceptions import DateRangeError, TimeZoneError

# <<<<Helper functions for time manipulation>>>>
UTC_MIDNIGHT = datetime.time(hour=0, minute=0, second=0, tzinfo=datetime.timezone.utc)
UTC_3AM = datetime.time(hour=3, minute=0, second=0, tzinfo=datetime.timezone.utc)


def get_current_utc_time():
    return datetime.datetime.now(datetime.timezone.utc)


def to_utc(time: datetime.datetime | datetime.time) -> datetime.datetime | datetime.time:
    """Converts datetime/time to UTC."""
    return time.astimezone(datetime.timezone.utc)


def to_local(time: datetime.datetime) -> datetime.datetime:
    """
    Converts UTC datetime object to local time zone
    """
    return time.astimezone()


def first_occurrence_after(t: datetime.time, dt: datetime.datetime):
    """
    Computes the datetime of the first occurrence of a date-agnostic time t
    after a datetime dt.
    """
    candidate = dt.replace(hour=t.hour, minute=t.minute, second=t.second, microsecond=0)

    if candidate <= dt:
        candidate += datetime.timedelta(days=1)

    return candidate


def last_occurrence_before(t: datetime.time, dt: datetime.datetime):
    """
    Computes the datetime of the last occurrence of a date-agnostic time t
    before a datetime dt.
    """
    candidate = dt.replace(hour=t.hour, minute=t.minute, second=t.second)

    if candidate >= dt:
        candidate -= datetime.timedelta(days=1)

    return candidate


def format_timedelta(diff: datetime.timedelta) -> str:
    hours = int(diff.total_seconds() // 3600)
    minutes = int((diff.total_seconds() % 3600) // 60)
    return f"{hours:+03d}:{minutes:02d}"


def validate_utc(t: datetime.time, name: str):
    if t.utcoffset() not in (None, datetime.timedelta(0)):
        diff = t.utcoffset()

        raise TimeZoneError(f"Expected {name} to be in UTC but is in UTC{format_timedelta(diff)}")

    if t.utcoffset() is None:
        return t.replace(tzinfo=datetime.timezone.utc)
    else:
        return t


def check_dates(start: datetime.datetime, end: datetime.datetime) -> None:
    """
    Checks if the date range is valid, since start datetime must come before end datetime
    """
    if start >= end:
        raise DateRangeError("START MUST COME BEFORE END!")


def format_datetime(t: datetime.datetime) -> str:
    if t.utcoffset() is None:  # Interpret no tzinfo as local time.
        diff = datetime.datetime.now().astimezone().utcoffset()
    else:
        diff = t.utcoffset()

    utc_signature = f"UTC{format_timedelta(diff)}"
    return (
        f"{str(t.day).zfill(2)}/{str(t.month).zfill(2)}/{str(t.year).zfill(4)} "
        f"{str(t.hour).zfill(2)}:{str(t.minute).zfill(2)} {utc_signature}"
    )


def format_timerange(start: datetime.datetime, end: datetime.datetime) -> str:
    return f"{format_datetime(start)} ==> {format_datetime(end)}"


def utc_to_local(time: datetime.datetime) -> datetime.datetime:
    """
    Returns a datetime object in the local timezone without timezone info.
    Used for database querying.
    """
    return time.astimezone().replace(tzinfo=None)
