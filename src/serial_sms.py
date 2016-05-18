import logging
import serial

from serial_protocol import Protocol


logger = logging.getLogger(__name__)

# Terminate String
TERMINATE = chr(26)
MULTIPART_HEADER = '\x05\x00\x0c'
INBOX_SIZE = 25


def _parse_cmgl_headers(s):
    try:
        index, status, origin, _, date, time = s.strip('+CMGL: ').split(',')
    except ValueError:
        return {
            'index': None,
            'status': None,
            'origin': None,
            'date': None,
            'time': None,
            'message': s,
        }
    y, m, d = date.split('/')
    date = '/'.join([m,d,y])
    return {
        'index': int(index),
        'status': status.replace('"', ''),
        'origin': origin.replace('"', ''),
        'date': date.replace('"', ''),
        'time': time.replace('"', '').split('+')[0],
        'message': None,
        }


def _parse_cmgl_response(ls):
    ch = cm = None
    messages = []
    for i, l in enumerate(ls):
        # This is a header. It is assumed that this is
        # the beginning of a new message.
        if l.startswith('+CMGL: '):
            m = cm = ch = None
            ch = l
            continue
        # This is the message body. Let's cm to the
        # current processed line.
        cm = l
        # If both header and message are filled,
        # add this pair to messages.
        if ch and cm:
            m = _parse_cmgl_headers(ch)
            m['message'] = cm
            messages.append(m)
            m = cm = ch = None
    return messages


def _merge_multipart(messages):
    """Merges any multipart messages. Expects a list of
    message objects (parsed from _parse_cmgl)."""
    all_messages = []
    multiparts = {}
    for m in messages:
        # If the message is a multipart message.
        if m['message'].startswith(MULTIPART_HEADER):
            mes = m['message'].strip(MULTIPART_HEADER)
            # We retrieve the message id and the actual
            # message.
            id, mes = mes.split('\x00', 1)
            # Cleanup message.
            mes = mes.replace('\x00', '')
            id = id[0][:2]
            m['message'] = mes
            if not multiparts.get(id, None):
                multiparts[id] = m
                continue
            multiparts[id]['message'] += mes
        else:
            all_messages.append(m)

    all_messages = all_messages + multiparts.values()
    return sorted(all_messages, key=lambda m: m['index'])


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
        self.transport.write('AT+CMGF=1\r')
        self.transport.readall()
        self.transport.write('AT+CMGS="%s"\r' % self.dest)

    def on_OK(self, l):
        logger.debug(l)

    def on_PROMPT(self, l):
        logger.debug(l)
        self.transport.write(self.msg)
        self.transport.write(TERMINATE)

    def on_CMGS(self, l):
        logger.debug(l)
        self.set_result((True, None))

    def on_ERROR(self, l):
        logger.error(l)
        self.set_result((False, l))


class SmsClear(Protocol):

    def __init__(self, ser):
        super(SmsClear, self).__init__(ser)
        self.index = range(1, INBOX_SIZE + 1)
        self.index.reverse()

    def loop_command(self):
        try:
            i = self.index.pop()
        except IndexError as e:
            self.set_result(True)
            return
        logger.info('Deleting message: %s' % i)
        self.transport.write('AT+CMGD=%s\r' % i)


class SmsInbox(Protocol):

    def __init__(self, ser, f='ALL'):
        super(SmsInbox, self).__init__(ser)
        self.f = f
        self._buffer = []

        self.on('+CME ERROR: ', self.on_ERROR)
        self.on('+CMS ERROR: ', self.on_ERROR)
        self.on('', self.on_ANY)

    def command(self):
        self.transport.write('AT+CMGF=1\r')
        self.transport.readall()

    def _process_buffer(self):
        return _merge_multipart(_parse_cmgl_response(self._buffer))

    def before(self):
        # Retrieve latest inbox.
        self.transport.write('AT+CMGL="%s"\r' % self.f)

    def after(self):
        logger.debug('Current _buffer: %s' % self._buffer)
        res = self._process_buffer()
        if res != None:
            self.set_result(res)

        # Reset buffer
        logger.debug('Clearing _buffer')
        self._buffer = []

    def on_ERROR(self, l):
        logger.error(l)
        self.set_result(l)

    def on_ANY(self, l):
        # Skip echo data
        if l.startswith('AT+CMGL'):
            return
        logger.debug('Adding to buffer: %s' % l)
        self._buffer.append(l)


if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    from serial_utils import BAUDRATE
    port = '/dev/tty.usbmodem14111'

    ser = serial.Serial(port, BAUDRATE, timeout=1)

    ## SmsSend
    ## Sends a sms message to a number.
    #print SmsSend(ser, '9175595283', 'woot jesse').run()

    ## SmsClear
    ## Deletes all messages in the inbox.
    #print SmsClear(ser).run()

    ## SmsInbox
    ## Retrieves the sim's inbox. Sorted from the most
    ## recent to the oldest.
    #print SmsInbox(ser).run()

    # SmsWait
    # Waits for a message to arrive at this number from a
    # specific number. If no message was received after the
    # timeout, None will be returned. If timeout is set to
    # 0, this function will run indefinitely until a
    # message is received.
    print SmsWait(ser, '+639175595283').run(1)
