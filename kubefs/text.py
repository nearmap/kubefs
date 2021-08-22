import datetime
import json
from typing import Any


def to_json(obj: Any) -> str:
    def default(obj):
        if isinstance(obj, (datetime.date, datetime.date)):
            return obj.isoformat()

    block = json.dumps(obj, sort_keys=True, indent=4, default=default)
    return block + "\n"
