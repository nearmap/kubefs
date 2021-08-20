import time
from datetime import datetime, timedelta, timezone
from typing import Union

import humanize


def date_now() -> datetime:
    return datetime.now(timezone.utc)


def elapsed_in_state(dt: Union[float, datetime]) -> str:
    if isinstance(dt, float):
        delta = timedelta(seconds=time.time() - dt)
    else:
        delta = date_now() - dt

    return humanize.naturaldelta(delta)


def humanize_delta(td: timedelta) -> str:
    fmt = ""

    if td.total_seconds() < 1:
        ms = int(td.total_seconds() * 1000)
        fmt = f"{ms}ms"

    elif td.total_seconds() < 60:
        secs = int(td.total_seconds())
        fmt = f"{secs}s"

    elif td.total_seconds() < 3600:
        mins = int(td.total_seconds() / 60)
        fmt = f"{mins}m"

    elif td.total_seconds() < 86400:
        hours = int(td.total_seconds() / 3600)
        fmt = f"{hours}h"

    elif td.days < 30:
        days = td.days
        fmt = f"{days}d"

    else:
        months = int(td.days / 30)
        fmt = f"{months}mo"

    return fmt
