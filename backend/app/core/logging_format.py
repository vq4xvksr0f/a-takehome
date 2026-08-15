"""Logging formatters for the app.

UtcIsoFormatter renders record timestamps as ISO-8601 UTC with a trailing 'Z'
(e.g. 2026-08-15T03:37:14Z) so log lines are unambiguous about timezone —
containers run in UTC, and a naive timestamp doesn't say so.
"""

import logging
from datetime import UTC, datetime


class UtcIsoFormatter(logging.Formatter):
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        dt = datetime.fromtimestamp(record.created, tz=UTC)
        # Millisecond precision like the default asctime, but explicitly UTC.
        return dt.strftime("%Y-%m-%dT%H:%M:%S") + f".{int(record.msecs):03d}Z"
