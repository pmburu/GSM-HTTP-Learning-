import logging
import time

import serial

from serial_protocol import Protocol


# Logger
logger = logging.getLogger(__name__)

# A bunch of constants for timeout.
NETWORK_VERY_SLOW = 20
NETWORK_SLOW = 10
NETWORK_NORMAL = 5
NETWORK_FAST = 2.5

# Terminate String
TERMINATE = chr(26)


class USSDSend(Protocol):

    def __init__(self, ser, cmd):
        super(USSDSend, self).__init__(ser)
        self.cmd = to_command_seq(cmd)
        self.cmd.reverse()
        self._buffer = []

        self.on('OK', self.on_OK)
        self.on('>', self.on_PROMPT)
        self.on('+CUSD: 0', self.on_CUSD_0)
        self.on('+CUSD: 1', self.on_CUSD_1)
        self.on('+CUSD: 2', self.on_CUSD_2)
        self.on('+CME ERROR', self.on_ERROR)

    def command(self):
        """Run our initial command."""
        cmd = self.cmd.pop()
        cmd = 'AT+CUSD=1,"%s",15\r' % cmd
        logger.debug(cmd)
        self.transport.write(cmd)

    def on_OK(self, l):
        logger.debug(l)

    def on_PROMPT(self, l):
        # If cmd is incomplete, return the last entry
        # from the buffer and terminate the current
        # USSD transaction.
        try:
            cmd = self.cmd.pop()
        except IndexError as e:
            self.set_result(self._buffer[-1])
            self.transport.write(TERMINATE)
            print(self.transport.readall())
            return
        logger.debug('> %s' % cmd)
        self.transport.write(cmd)
        self.transport.write(TERMINATE)

    def on_CUSD_0(self, l):
        logger.debug(l)
        self.set_result(l)

    def on_CUSD_1(self, l):
        logger.debug(l)
        l = l.replace('+CUSD: 1,"', '')
        l = l.rstrip('",15')
        self._buffer.append(l)

    def on_CUSD_2(self, l):
        logger.debug(l)
        l = l.replace('+CUSD: 2,"', '')
        l = l.rstrip('",15')
        self._buffer.append(l)
        self.set_result(l)

    def on_ERROR(self, l):
        logger.error(l)
        self.set_error(l)


def to_command_seq(s):
    """Translates a string command into a command sequence."""
    # Remove pound signs
    seq = [_s for _s in s.replace('#', '').split('*') if _s]
    seq[0] = '*%s#' % seq[0]
    return seq


if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    from serial_utils import BAUDRATE
    port = '/dev/tty.usbmodem14211'

    ser = serial.Serial(port, BAUDRATE, timeout=1)
    ## Test single USSD bookmark
    #print USSDSend(ser, ['*143*1*1*7#']).run()

    # Test Incomplete USSD bookmark
    # XXX: This doesn't work. As some USSD services are
    # very stateful. If you intend to pass an incomplete
    # menu, you need to `dance` (See dance example below).
    print USSDSend(ser, ['*143*1*1*7#']).run()

    ## Test USSD dance
    #print USSDSend(ser, ['*143#', '1', '1', '7']).run()

    ## Test Incomplete USSD dance
    #print USSDSend(ser, ['*143#', '2', '1']).run()
