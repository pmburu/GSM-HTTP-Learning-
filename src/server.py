from functools import partial
import serial_gsm
import serial
import initialize
import net_utils


SERIAL_BAUDRATE = 115200
SERIAL_TIMEOUT = 0.1
Serial = partial(serial.Serial, baudrate=SERIAL_BAUDRATE,
    timeout=SERIAL_TIMEOUT)


print 'Initializing modem...'
# Initialize modem phones.
ports = {m: None for m in initialize.get_modems()}
numbers = {}
serials = {}
unused_ports = []


def check_modem(ser):
    try:
        ser.write('AT')
        return True
    except:
        return False


# Parse numbers.
for port in ports.keys():
    print 'initializing port %s' % port
    try:
        _ser = Serial(port)
    except:
        unused_ports.append(port)
        continue
    if not check_modem(_ser):
        continue
    number = serial_gsm.sim_msisdn(_ser)
    if number:
        serials[number] = _ser
        ports[port] = number
        numbers[number] = port
print 'Modem initialized!'


from flask import Flask, jsonify, abort, request


app = Flask(__name__)


def ser_or_404(number):
    ser = serials.get(number, None)
    if not ser:
        return abort(404)
    return ser


def port_or_404(number):
    port = numbers.get(number, None)
    if not port:
        return abort(404)
    return port


@app.route('/system/available_numbers')
def api_available_numbers():
    return jsonify({'numbers': serials.keys()})


@app.route('/system/unused_ports')
def api_unused_ports():
    return jsonify({'ports': unused_ports})


@app.route('/modems/<number>/call', methods=['POST'])
def api_call(number):
    ser = ser_or_404(number)

    dest_number = request.form['number']
    duration = int(request.form.get('duration', 0))

    res = serial_gsm.call(ser, dest_number, duration=duration)
    return jsonify(res)


@app.route('/modems/<number>/wait_for_call', methods=['POST'])
def api_wait_for_call(number):
    ser = ser_or_404(number)
    duration = int(request.form.get('duration', 0))
    res = serial_gsm.wait_and_answer_call(ser, duration=duration)
    return jsonify(res)


@app.route('/modems/<number>/send_sms', methods=['POST'])
def api_send_sms(number):
    ser = ser_or_404(number)
    recipient = request.form['number']
    message = request.form['message']
    res = serial_gsm.send_sms(ser, recipient, message)
    return jsonify(res)


@app.route('/modems/<number>/inbox')
def api_inbox(number):
    ser = ser_or_404(number)
    return jsonify({
        'messages': serial_gsm.inbox_messages(ser)
    })


@app.route('/modems/<number>/inbox', methods=['DELETE'])
def api_clear_inbox(number):
    ser = ser_or_404(number)
    return jsonify(serial_gsm.delete_inbox_messages(ser))


@app.route('/modems/<number>/wait_for_sms')
def api_wait_for_sms(number):
    origin = request.args['origin']
    timeout = int(request.args.get('timeout', 0))
    res = serial_gsm.wait_for_sms(ser, origin, timeout)
    return jsonify(res)


@app.route('/modems/<number>/ussd', methods=['POST'])
def api_send_ussd(number):
    ser = ser_or_404(number)
    command = request.form['command']
    timeout = int(request.form.get('timeout', 0))
    res = serial_gsm.ussd_send(ser, command, timeout=timeout)
    return jsonify(res)


@app.route('/modems/<number>/data', methods=['POST'])
def api_data_request(number):
    # TODO: Update wvdial config.
    # TODO: Connect using wvdial.
    # TODO: Flush DNS
    url = request.form['url']
    timeout = request.form.get('timeout', 0)
    with net_utils.use_interface('wlan0'):
        try:
            r = requests.get(url, timeout=timeout)
        except requests.ConnectionError:
            return jsonify({
                'error': 'Failed to connect.',
                'url': url,
                'response_body_size': None,
                'response_header_size': None,
                'response_status_code': None,
            })

    return jsonify({
        'error': None,
        'url': url,
        'response_body_size': len(r.text),
        'response_header_size': None,
        'response_status_code': r.status_code,
    })


if __name__ == '__main__':
    from werkzeug.debug import DebuggedApplication
    app.debug = True
    app = DebuggedApplication(app, evalex=True)
    from gevent.wsgi import WSGIServer
    WSGIServer(('0.0.0.0', 3000), app).serve_forever()
