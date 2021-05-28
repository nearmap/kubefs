import datetime
import json


def to_json(obj) -> str:
    def default(obj):
        if isinstance(obj, (datetime.date, datetime.date)):
            return obj.isoformat()

    block = json.dumps(obj, sort_keys=True, indent=4, default=default)
    return block + "\n"
