import logging

from serial_utils import clean_lines


logger = logging.getLogger(__name__)


class Event(object):

    def __init__(self):
        self._events = {}

    def emit(self, event, data):
        cbs = self._events.get(event, [])
        for c in cbs:
            c(data)

    def on(self, event, cb):
        cbs = self._events.get(event, [])
        cbs.append(cb)
        self._events[event] = cbs


class Protocol(Event):

    def __init__(self, ser):
        super(Protocol, self).__init__()
        self.transport = ser
        self._result = None

    def set_result(self, res):
        self._result = res

    def result(self):
        return self._result

    def command(self):
        raise NotImplemented()

    def emit(self, l):
        """Overrides Event.emit() so we only need to
        provide the data we've been given."""
        for be in self._events.keys():
            if l.startswith(be):
                super(Protocol, self).emit(be, l)

    def run(self):
        """Executes the self.command() then runs the event
        loop. Terminates once self.result() no longer
        returns a False'y value."""
        self.command()
        while True:
            logger.debug('looping...')
            if self.result():
                return self.result()
            for l in clean_lines(self.transport.readall().split('\r\n')):
                logger.debug(l)
                self.emit(l)
