from datetime import datetime, timezone


def utc_now() -> datetime:
    """Current UTC time as a naive datetime, matching the naive values already stored in the database."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
