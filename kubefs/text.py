import datetime
import json
from typing import Any, Dict


def to_json(obj: Any) -> str:
    def default(obj):
        if isinstance(obj, (datetime.date, datetime.date)):
            return obj.isoformat()

    block = json.dumps(obj, sort_keys=True, indent=4, default=default)
    return block + "\n"


def to_dict(obj: Any) -> Dict[Any, Any]:
    """Patched version of v1_pod.V1Pod.to_dict() to avoid serializing fields
    whose value is None."""

    result = {}

    for attr in obj.openapi_types:
        value = getattr(obj, attr)

        # we don't want to emit None values just because the field is part of
        # the openapi type
        if value is None:
            continue

        if isinstance(value, list):
            result[attr] = list(
                map(lambda x: to_dict(x) if hasattr(x, "to_dict") else x, value)
            )
        elif hasattr(value, "to_dict"):
            result[attr] = to_dict(value)
        elif isinstance(value, dict):
            result[attr] = dict(
                map(
                    lambda item: (item[0], to_dict(item[1]))
                    if hasattr(item[1], "to_dict")
                    else item,
                    value.items(),
                )
            )
        else:
            result[attr] = value

    return result
