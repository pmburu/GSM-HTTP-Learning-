from serial_protocol import Protocol


class WaitCall(Protocol):
    """WaitCall

    Protocol implementation for waiting a call.
    """

    def __init__(self, ser, timeout=0):
        super(WaitCall, self).__init__(ser)
        self.timeout = timeout

    def command(self):
        pass


class SendCall(Protocol):
    pass
