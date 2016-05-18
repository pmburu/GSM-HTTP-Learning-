import logging
import serial

from serial_protocol import Protocol


logger = logging.getLogger(__name__)

# Terminate String
TERMINATE = chr(26)


def send_sms(ser, recipient, message):
    """Sends an sms to a recipient (msisdn)."""
    ser.write('AT+CMGF=1\r')
    res = wait_for_strs(ser, ['OK'])
    ser.write('AT+CMGS="%s"\r' % recipient)
    time.sleep(0.5)
    ser.write('%s\r' % message)
    ser.write(chr(26))
    res = wait_for_strs(ser, ['OK', 'ERROR'])
    if 'ERROR' in res:
        return {'success': False, 'res': res, 'error': GENERIC_SYSTEM_ERROR}
    return {'success': True, 'res': res, 'error': None}



class SmsSend(Protocol):

    def __init__(self, ser, dest, msg):
        super(SmsSend, self).__init__(ser)
        self.dest = dest
        self.msg = msg

        self.on('OK', self.on_OK)
        self.on('>', self.on_PROMPT)
        self.on('+CMGS: ', self.on_CMGS)
        self.on('+CME ERROR', self.on_ERROR)
        self.on('+CMS ERROR', self.on_ERROR)

    def command(self):
        #self.transport.write('AT+CMGF=1\r')
        self.transport.write('AT+CMGS="%s"\r' % self.dest)

    def on_OK(self, l):
        logger.debug(l)

    def on_PROMPT(self, l):
        logger.debug(l)
        self.transport.write(self.msg)
        self.transport.write(TERMINATE)

    def on_CMGS(self, l):
        logger.debug(l)
        self.set_result(True)

    def on_ERROR(self, l):
        logger.error(l)
        self.set_result(False)


if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    from serial_utils import BAUDRATE
    port = '/dev/tty.usbmodem14111'

    ser = serial.Serial(port, BAUDRATE, timeout=1)

    print SmsSend(ser, '09175595283', 'hello jesse').run()
