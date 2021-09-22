import json
import logging
import os
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Union

import humanize
from aiohttp import BasicAuth
from dateutil.parser import parse as parse_date

from kube.config import Context
from kube.tools.timekeeping import date_now


class BearerAuth(BasicAuth):
    """
    aiohttp only ships BasicAuth and does:

        def update_auth(self, auth: Optional[BasicAuth]) -> None:
            ...
            if not isinstance(auth, helpers.BasicAuth):

    So to slot into this API we need a subclass of BasicAuth, which is what
    we're doing here. It's a bit hacky but it works.
    """

    def __new__(cls, token: str) -> "BearerAuth":
        return super().__new__(cls, token)  # type: ignore

    def __init__(self, token: str) -> None:
        self.token = token

    def encode(self) -> str:
        return f"Bearer {self.token}"


AuthBase = Union[BasicAuth, BearerAuth]


class AuthContainer:
    def __init__(
        self, *, auth: Optional[AuthBase], expiry_date: Optional[datetime] = None
    ) -> None:
        self.auth = auth
        self.expiry_date = expiry_date

    def has_expired(self) -> bool:
        if self.expiry_date is None:
            return False

        # Trigger a refresh a few minutes before the deadline to account for
        # clock skew. Otherwise we assume the credentials are still good but
        # they may be considered expired by the API server.
        return date_now() >= (self.expiry_date - timedelta(minutes=5))


class AuthProvider:
    def __init__(self, context: Context, logger=None) -> None:
        self.context = context
        self.logger = logger or logging.getLogger("auth")

        self.container: Optional[AuthContainer] = None  # lazy attribute

    def create_container(self) -> AuthContainer:
        if self.context.user.username and self.context.user.password:
            auth = BasicAuth(
                login=self.context.user.username, password=self.context.user.password
            )
            return AuthContainer(auth=auth)

        elif self.context.user.exec:
            cmd = self.context.user.exec
            args = [cmd.command] + cmd.args

            environ = os.environ
            environ.update(cmd.env)

            proc = subprocess.Popen(
                args=args,
                env=environ,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            stdout_bytes, stderr_bytes = proc.communicate()
            stdout, stderr = stdout_bytes.decode(), stderr_bytes.decode()

            if proc.returncode == 0:
                doc = json.loads(stdout)

                status = doc.get("status")
                token = status.get("token")
                expirationTimestamp = status.get("expirationTimestamp")

                expiry_date = parse_date(expirationTimestamp)
                time_left = humanize.naturaldelta(expiry_date - date_now())

                self.logger.info(
                    "[%s] Successfully obtained exec credentials valid until: %s, "
                    "will expire in: %s",
                    self.context.short_name,
                    expiry_date,
                    time_left,
                )

                auth = BearerAuth(token=token)
                return AuthContainer(auth=auth, expiry_date=expiry_date)

            self.logger.error(
                "Failed to obtain exec credentials:"
                "\nexit_code: %s\nstdout: <<<%s>>>\nstderr: <<<%s>>>",
                proc.returncode,
                stdout.strip(),
                stderr.strip(),
            )

        return AuthContainer(auth=None)

    def get_auth(self) -> Optional[AuthBase]:
        if self.container is None or self.container.has_expired():
            self.container = self.create_container()

        return self.container.auth
