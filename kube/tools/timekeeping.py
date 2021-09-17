from datetime import datetime, timezone


def date_now() -> datetime:
    return datetime.now(timezone.utc)
