from typing import Optional


def disp_secret_string(input: Optional[str]) -> str:
    return "SET" if input is not None else "UNSET"


def disp_secret_blob(input: Optional[str]) -> Optional[str]:
    return "[%s bytes]" % len(input) if input is not None else None
