from datetime import datetime
from typing import Optional

from dateutil.parser import parse as parse_date


def maybe_parse_date(dt: Optional[str]) -> Optional[datetime]:
    if dt:
        return parse_date(dt)

    return None
