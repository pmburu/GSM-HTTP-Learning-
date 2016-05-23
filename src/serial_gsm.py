import time
import socket
import fcntl
import struct

from serial_ussd import USSDSend


true_socket = socket.socket


MULTIPART_HEADER = '\x05\x00\x0c'
CALL_RES_STATES = [
    'OK',  # Call is successfully conncted.
    'BUSY',  # Call is cancelled by the other end.
    'NO CARRIER',  # Call is ended?
    'NO DIALTONE',  # No dialtone...
    'CME ERROR:',  # Call timeout.
]
GENERIC_SYSTEM_ERROR = 'Modem might be out of coverage. Check modem and try again.'


def make_bound_socket(ip):
    def bound_socket(*a, **k):
        sock = true_socket(*a, **k)
        sock.bind((ip, 0))
        return sock
    return bound_socket


def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,
        struct.pack('256s', ifname[:15])
    )[20:24])


def _parse_cusd(s):
    """Parses a cusd response."""
    return s.strip()\
            .rstrip()\
            .replace('+CUSD: 1,"', '')\
            .replace('+CUSD: 2,"', '')\
            .replace('",15', '')


def _parse_cpbr_row(s):
    """Parses a cpbr row data into a dictionary."""
    index, number, type, name = s.strip('+CPBR: ').split(',')
    return {
        'index': int(index),
        'number': number.replace('"', '').rstrip(),
        'type': int(type),
        'name': name.replace('"', '').rstrip(),
    }


def _parse_cpbr(s):
    """Parses cpbr response."""
    s = s.strip().rstrip()
    _numbers = []
    for l in s.split('\n'):
        if l[:6] == '+CPBR:':
            _numbers.append(_parse_cpbr_row(l))
    return _numbers


def _parse_cmgl_header(s):
    """Parses a cmgl row data into a dictionary."""
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


def _merge_multipart_messages(messages):
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


def _parse_cmgl(s):
    """Parses a cmgl response."""
    res = s.strip().rstrip()
    parts = []
    messages = []
    for l in res.split('\n')[1:]:
        l = l.strip().rstrip()
        # The response has been fully processed. Let's
        # return the last message set.
        if l[:2] == 'OK':
            if not parts and not messages:
                break
            m = '\n'.join(parts)
            message['message'] = m
            parts = []
            messages.append(message)
            break

        # Check if the current line is a header.
        if l[:6] == '+CMGL:':
            if parts:
                m = '\n'.join(parts)
                message['message'] = m
                parts = []
                messages.append(message)
            message = _parse_cmgl_header(l)
            continue

        # This must be a fragment of a message.
        if l:
            parts.append(l)

    return _merge_multipart_messages(messages)


def wait_for_strs(ser, strs, timeout=0):
    """Waits for any of the provided strings in the serial
    stream.

    If `timeout` is set to 0, this function blocks until
    a provided string matches.

    If `timeout` is set to > 1, this function blocks until
    a provided string matches or until the provided timeout.
    """
    started = int(time.time())
    _buffer = ''
    while True:
        res = ser.readall()
        _buffer += res
        for s in strs:
            if s in res:
                return _buffer
        if timeout:
            elapsed = int(time.time()) - started
            if elapsed >= timeout:
                return 'CME ERROR: TIMEOUT'


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


def delete_inbox_message(ser, index):
    """Deletes an inbox message given an index."""
    ser.write('AT+CMGD=%s\r' % index)
    res = wait_for_strs(ser, ['OK', 'ERROR'])
    if 'ERROR' in res:
        return False
    return True


def delete_inbox_messages(ser):
    """Deletes all inbox messages."""
    try:
        for i in xrange(26):
            delete_inbox_message(ser, i)
    except Exception:
        return {'success': False}

    return {'success': True}


def inbox_messages(ser):
    """Returns all the inbox messages."""
    ser.write('AT+CMGF=1\r')
    res = wait_for_strs(ser, ['OK'])
    ser.write('AT+CMGL=ALL\r')
    res = wait_for_strs(ser, ['OK'])
    return _parse_cmgl(res)


def wait_for_sms(ser, origin, timeout=0):
    """Waits for a message from a specific origin."""
    started = int(time.time())
    while True:
        messages = inbox_messages(ser)
        for m in messages:
            if origin.lower() in m['origin'].lower():
                return {'message': m, 'error': None}
        if timeout:
            elapsed = int(time.time()) - started
            if elapsed > timeout:
                return {'message': None, 'error': 'Wait for SMS timed-out.'}


def sim_msisdn(ser):
    """Returns the sim's msisdn."""
    ser.write('AT+CPBS=SM\r')
    res = wait_for_strs(ser, ['OK', 'ERROR'], timeout=5)
    if 'ERROR' in res:
        print 'error: %s' % res
        return False
    ser.write('AT+CPBR=1,100\r')
    res = wait_for_strs(ser, ['OK', 'ERROR'], timeout=5)
    if 'ERROR' in res:
        print 'error: %s' % res
        return False
    numbers = _parse_cpbr(res)
    for num in numbers:
        if num['name'] == 'My Number':
            return num['number']


def call(ser, number, duration=0, timeout=30):
    """Dials a number.

    Waits for a connection or cancels the attempt after a
    provided `duration`. If the provided `timeout` is 0,
    the call blocks until a connection is made.

    Once the call has been connected, if a `duration` is
    set, the call proceeds until the specified duration.
    """
    ser.write('ATD%s;\r' % number)
    res = wait_for_strs(ser, CALL_RES_STATES, timeout=timeout)
    # If we receive a 'CME ERROR: 100', it means that we
    # got a busy. And for some weird reason, the data is not
    # streamed into the serial comm. What we do here then
    # is send a `\r` to refresh buffer.
    if 'CME ERROR:' in res:
        ser.write('\r')
        res = wait_for_strs(ser, CALL_RES_STATES, timeout=timeout)
    # If the call has not been successfully connected, the
    # function exits.
    if 'OK' not in res:
        return {'connected': False, 'duration': 0, 'res': res}
    started = int(time.time())
    # Let's wait until the call is bound to end or the call
    # has been ended from the other side.
    res = wait_for_strs(ser, CALL_RES_STATES, timeout=duration)
    ser.write('AT+CHUP\r')
    res = wait_for_strs(ser, CALL_RES_STATES, timeout=duration)
    return {'connected': True, 'duration': int(time.time()) - started, 'res': res}


def wait_and_answer_call(ser, duration=0, timeout=30):
    """Waits for a call and answers it.

    The set `duration` is the expected duration for the
    call. If the call hasn't been ended from the other side
    after the duration, the call is ended from this side.

    If a set `duration` the call is ended prematurely
    """
    res = wait_for_strs(ser, ['RING'], timeout=timeout)
    if 'RING' not in res:
        return {'connected': False, 'duration': 0}
    ser.write('ATA\r')
    res = wait_for_strs(ser, ['OK'], timeout=timeout)
    started = int(time.time())
    res = wait_for_strs(ser, ['NO CARRIER'], timeout=duration)
    # If the call was not ended from the other side and
    # we've reached the expected call duration.
    if not 'NO CARRIER' in res:
        ser.write('AT+CHUP\r')
        wait_for_strs(ser, ['OK'], timeout=timeout)
    return {'connected': True, 'duration': int(time.time()) - started}


def ussd_send(ser, command, timeout=0):
    """Makes an USSD request. Returns the response of the
    command.

    For partial USSD commands, the function only returns
    once the server has terminated the USSD session. This
    does not follow the provided timeout.
    """
    err, res = USSDSend(ser, command).run(timeout)
    return {
        'success': True,
        'message': res,
        'error': err,
    }
    ## XXX: OLD CODE
    ## We clear any existing USSD messages or uncleared
    ## buffer.
    #res = wait_for_strs(ser, ['ERROR', 'OK', '+CUSD: 2', '+CUSD: 1'], timeout=1)
    #ser.write('AT+CUSD=1,"%s",15\r' % command)
    #res = wait_for_strs(ser, ['OK', 'ERROR'], timeout=timeout)
    ## If an error occurs, 
    #if 'ERROR' in res:
    #    return {'success': False, 'message': None, 'error': res}
    #res = wait_for_strs(ser, ['ERROR', '+CUSD: 2', '+CUSD: 1'], timeout=timeout)
    ## If an error occurs, 
    #if 'ERROR' in res:
    #    return {'success': False, 'message': None, 'error': res}
    ## Let's wait for the server to terminate the session.
    #if '+CUSD: 1' in res:
    #    wait_for_strs(ser, ['ERROR'], timeout=0)
    #return {'success': True, 'message': _parse_cusd(res), 'error': None}


def check_modem(ser, timeout=0.5):
    """Checks the modem if it responds to a test command."""
    ser.write('AT\r')
    res = wait_for_strs(ser, ['OK'], timeout=timeout)
    if 'ERROR' in res:
        return False
    return True


def check_signal(ser, timeout=0):
    """Checks the modem current signal quality."""
    ser.write('AT+CSQ\r')
    res = wait_for_strs(ser, ['ERROR', 'OK'], timeout=timeout)
    if 'ERROR' in res:
        return {'error': res, 'rssi': None, 'ber': None}
    # Parse the signal quality
    m = res.split('+CSQ:')[1].replace('OK', '').replace('\n', '').strip()
    rssi, ber = m.split(',')
    return {'error': None, 'rssi': rssi, 'ber': ber}


if __name__ == '__main__':
    import sys
    import logging
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    import serial
    import time
    number = "9062806806"
    #port = '/dev/ttyACM2'
    port = '/dev/tty.usbmodem14111'
    #ports = ['/dev/ttyACM%s' % n for n in xrange(64)]
    print 'reading...', port
    ser = serial.Serial(port, 115200, timeout=0.2)
    res = str(sim_msisdn(ser))
    print "woot: ", number == res
    print 'port: %s -- %s' % (port, res)
    balance = ussd_send(ser, '*143*2*1*1#', timeout=0)
    print 'balance: %s' % balance
