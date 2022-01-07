class ClientOperationParams:
    pass


class LogStreamingParams(ClientOperationParams):
    def __init__(self, *, tail_lines: int = 0) -> None:
        # how many log lines from the past to fetch (ie. from the circular
        # buffer that are prior to the cursor)
        self.tail_lines = tail_lines
