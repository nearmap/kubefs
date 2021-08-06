import logging

from aiohttp import BasicAuth, ClientSession

from akube.client_state import ClientState
from kube.config import Context


class AsyncClient:
    def __init__(
        self, *, session: ClientSession, state: ClientState, logger=None
    ) -> None:
        self.session = session
        self.state = state
        self.logger = logger or logging.getLogger("aclient")

    @classmethod
    def create(
        cls, *, context: Context, session: ClientSession, logger=None
    ) -> "AsyncClient":
        basic_auth = None

        if context.user.username and context.user.password:
            basic_auth = BasicAuth(
                login=context.user.username, password=context.user.password
            )

        ssl_context = context.create_ssl_context()

        state = ClientState(basic_auth=basic_auth, ssl_context=ssl_context)
        self = cls(session=session, state=state, logger=logger)

        return self
