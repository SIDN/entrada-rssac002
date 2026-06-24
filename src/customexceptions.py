# I/O Errors
class PermanentError(Exception):
    pass


class TransientError(Exception):
    pass


# Time Errors
class TimeZoneError(Exception):
    pass


class DateRangeError(Exception):
    pass


# Report generation errors
class NoDataException(Exception):
    pass


class InvalidReportError(Exception):
    pass
