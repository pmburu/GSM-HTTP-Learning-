from functools import partial
import serial_gsm
import serial
import initialize
import net_utils
import requests
import time
import ftp_utils


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


# Parse numbers.
for port in ports.keys():
    print 'initializing port %s' % port
    try:
        _ser = Serial(port)
    except:
        print 'unable to load port'
        unused_ports.append(port)
        continue
    if not serial_gsm.check_modem(_ser):
        print 'failed to check modem'
        continue
    number = serial_gsm.sim_msisdn(_ser)
    print 'got number: %s' % number
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
    # We were unable to connect the call.
    if res.get('connected', False):
        return jsonify(res), 400
    return jsonify(res)


@app.route('/modems/<number>/wait_for_call', methods=['POST'])
def api_wait_for_call(number):
    ser = ser_or_404(number)
    duration = int(request.form.get('duration', 0))
    res = serial_gsm.wait_and_answer_call(ser, duration=duration)
    # We were unable to connect the call.
    if res.get('connected', False):
        return jsonify(res), 400
    return jsonify(res)


@app.route('/modems/<number>/send_sms', methods=['POST'])
def api_send_sms(number):
    ser = ser_or_404(number)
    recipient = request.form['number']
    message = request.form['message']
    res = serial_gsm.send_sms(ser, recipient, message)
    # We were unable to send the sms
    if res.get('success', False):
        return jsonify(res), 500
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
    ser = ser_or_404(number)
    origin = request.args['origin']
    timeout = int(request.args.get('timeout', 0))
    res = serial_gsm.wait_for_sms(ser, origin, timeout)
    # SMS waited probably never came. Try again?
    if res.get('error', 'an error'):
        return jsonify(res), 400
    return jsonify(res)


@app.route('/modems/<number>/ussd', methods=['POST'])
def api_send_ussd(number):
    ser = ser_or_404(number)
    command = request.form['command']
    timeout = int(request.form.get('timeout', 0))
    res = serial_gsm.ussd_send(ser, command, timeout=timeout)
    # USSD requests are more prone to system errors.
    if res.get('success', False):
        return jsonify(res), 500
    return jsonify(res)


@app.route('/modems/<number>/data', methods=['POST'])
def api_data_request(number):
    url = request.form['url']
    timeout = int(request.form.get('timeout', 0))
    port = port_or_404(number)
    # TODO: Turn the ff into a required argument in the
    # future.
    apn = request.form.get('apn', 'http.globe.com.ph')
    dial = request.form.get('dial', '*99#')
    wait_connect = int(request.form.get('wait_connect', 5))

    # Optionally trigger a dns refresh in each request
    refresh_dns = request.form.get('refresh_dns', 'false').lower() == 'true'

    if refresh_dns:
        net_utils.flush_dns()

    proc = net_utils.connect_wvdial(port, apn, wait_connect=wait_connect)

    # TODO: Implement a dynamic interface system so we can handle multiple
    # connected interfaces in a single server.
    res, err = net_utils.check_if_connected('ppp0')

    if not res:
        proc.terminate()
        return jsonify({
            'error': 'Unable to establish a connection to the network: %s. Try increasing the `wait_connect` parameter.' % err,
            'url': url,
            'response_body_size': None,
            'response_header_size': None,
            'response_status_code': None,
        }), 500


    with net_utils.use_interface('ppp0'):
        try:
            r = requests.get(url, timeout=timeout)
        except requests.ConnectionError:
            proc.terminate()
            return jsonify({
                'error': 'Request timed-out. Unable to connect to the url specified. Try increasing the `timeout` parameter.',
                'url': url,
                'response_body_size': None,
                'response_header_size': None,
                'response_status_code': None,
            })

    # Let's close the interface, finally.
    proc.terminate()

    return jsonify({
        'error': None,
        'url': url,
        'response_body_size': len(r.text),
        'response_header_size': None,
        'response_status_code': r.status_code,
    })


@app.route('/modems/<number>/ftp', methods=['POST'])
def api_ftp_request(number):
    ftp_filename = request.form['ftp_filename']
    ftp_host = request.form['ftp_host']
    ftp_file = request.form['ftp_file']
    ftp_path = request.form['ftp_path']
    ftp_port = int(request.form.get('ftp_port', 21))
    ftp_username = request.form.get('ftp_username', None)
    ftp_password = request.form.get('ftp_password', None)

    timeout = int(request.form.get('timeout', 0))
    port = port_or_404(number)
    # TODO: Turn the ff into a required argument in the
    # future.
    apn = request.form.get('apn', 'http.globe.com.ph')
    dial = request.form.get('dial', '*99#')
    wait_connect = int(request.form.get('wait_connect', 5))

    # Optionally trigger a dns refresh in each request
    refresh_dns = request.form.get('refresh_dns', 'false').lower() == 'true'

    if refresh_dns:
        net_utils.flush_dns()

    proc = net_utils.connect_wvdial(port, apn, wait_connect=wait_connect)

    # TODO: Implement a dynamic interface system so we can handle multiple
    # connected interfaces in a single server.
    res, err = net_utils.check_if_connected('ppp0')

    if not res:
        proc.terminate()
        return jsonify({
            'error': 'Unable to establish a connection to the network: %s. Try increasing the `wait_connect` parameter.' % err,
            'success': False,
        }), 500


    with net_utils.use_interface('ppp0'):
        try:
            ftp_utils.upload(
                ftp_file,
                ftp_host,
                ftp_filename=ftp_filename,
                ftp_port=ftp_port,
                ftp_username=ftp_username,
                ftp_password=ftp_password,
                upload_path=ftp_path,
                timeout=timeout
            )
        except Exception:
            proc.terminate()
            return jsonify({
                'error': 'Request timed-out. Failed to upload. Try increasing the `timeout` parameter.',
                'success': False,
            })

    # Let's close the interface, finally.
    proc.terminate()

    return jsonify({
        'error': None,
        'success': True,
    })


if __name__ == '__main__':
    from werkzeug.debug import DebuggedApplication
    app.debug = True
    app = DebuggedApplication(app, evalex=True)
    from gevent.wsgi import WSGIServer
    WSGIServer(('0.0.0.0', 3000), app).serve_forever()
