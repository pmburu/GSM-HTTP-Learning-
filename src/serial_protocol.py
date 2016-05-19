import logging
import time

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
        self._has_result = False

    def set_result(self, res):
        self._has_result = True
        self._result = res

    @property
    def result(self):
        return self._result

    def command(self):
        pass

    def before(self):
        pass

    def after(self):
        pass

    def emit(self, l):
        """Overrides Event.emit() so we only need to
        provide the data we've been given."""
        for be in self._events.keys():
            if l.startswith(be):
                super(Protocol, self).emit(be, l)

    def fn(self):
        """Primary function to execute on each loop."""
        for l in clean_lines(self.transport.readall().split('\r\n')):
            self.emit(l)

    def run(self, timeout=0):
        """Executes the self.command() then runs the event
        loop. Terminates once self.result() no longer
        returns a False'y value.

        If a timeout is set, this function runs until the
        specified timeout. Returns the default result
        value (None).

        Executes in this order:
        command
            -> loop(
                -> before
                -> [result -> timeout]
                -> fn
                -> after
            )
        """
        _started = int(time.time())
        self.command()
        while True:
            logger.debug('Looping...')
            logger.debug('Before...')
            self.before()

            if self._has_result:
                return self.result

            duration = int(time.time()) - _started
            if timeout != 0:
                if duration > timeout:
                    logger.debug('Request Timed-out')
                    return self.result

            self.fn()

            logger.debug('After...')
            self.after()


