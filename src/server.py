from functools import partial
import serial_gsm
import serial
import initialize


SERIAL_BAUDRATE = 115200
SERIAL_TIMEOUT = 0.1
Serial = partial(serial.Serial, baudrate=SERIAL_BAUDRATE,
    timeout=SERIAL_TIMEOUT)


print 'Initializing modem...'
# Initialize modem phones.
ports = {m: None for m in initialize.get_modems()}
print initialize.get_modems()
numbers = {}


# Parse numbers.
for port in ports.keys():
    ser = Serial(port)
    number = serial_gsm.sim_msisdn(ser)
    if number:
        ports[port] = number
        numbers[number] = port
print 'Modem initialized!'


from flask import Flask, jsonify, abort, request


app = Flask(__name__)


@app.route('/modems/<number>/prep_bal')
def api_number_bal(number):
    port = numbers.get(number, None)
    if not port:
        abort(404)
    return jsonify({'balance': 0})


@app.route('/system/available_numbers')
def api_available_numbers():
    return jsonify({'numbers': numbers.keys()})


@app.route('/system/unused_ports')
def api_unused_ports():
    return jsonify({'ports': [p for p in ports.values() if p]})


@app.route('/modems/<number>/call', methods=['POST'])
def api_call(number):
    port = numbers.get(number, None)
    if not port:
        return abort(404)

    dest_number = request.form['number']
    duration = int(request.form.get('duration', 0))

    ser = Serial(port)
    res = serial_gsm.call(ser, dest_number, duration=duration)
    return jsonify(res)


@app.route('/modems/<number>/wait_for_call', methods=['POST'])
def api_wait_for_call(number):
    port = numbers.get(number, None)
    if not port:
        return abort(404)

    duration = int(request.form.get('duration', 0))

    ser = Serial(port)
    res = serial_gsm.wait_and_answer_call(ser, duration=duration)
    return jsonify(res)


@app.route('/modems/<number>/send_sms', methods=['POST'])
def api_send_sms(number):
    port = numbers.get(number, None)
    if not port:
        return abort(404)

    recipient = request.form['number']
    message = request.form['message']

    ser = Serial(port)
    res = serial_gsm.send_sms(ser, recipient, message)
    return jsonify(res)


@app.route('/modems/<number>/inbox')
def api_inbox(number):
    port = numbers.get(number, None)
    if not port:
        return abort(404)
    
    return jsonify({
        'messages': serial_gsm.inbox_messages(ser)
    })


@app.route('/modems/<number>/inbox', methods=['DELETE'])
def api_clear_inbox(number):
    port = numbers.get(number, None)
    if not port:
        return abort(404)

    ser = Serial(port)
    return jsonify(serial_gsm.delete_inbox_messages(ser))


@app.route('/modems/<number>/ussd', methods=['POST'])
def api_send_ussd(number):
    port = numbers.get(number, None)
    if not port:
        return abort(404)

    command = request.form['command']
    timeout = int(request.form.get('timeout', 0))

    ser = Serial(port)
    res = serial_gsm.ussd_send(ser, command, timeout=timeout)
    return jsonify(res)
