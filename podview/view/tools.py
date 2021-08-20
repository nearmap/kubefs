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
