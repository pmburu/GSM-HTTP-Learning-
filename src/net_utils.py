from mock import patch
from contextlib import contextmanager
import serial_gsm
import urllib2
import socket
import time
import requests
import fcntl
import struct
import socket
import subprocess


true_socket = socket.socket


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


@contextmanager
def use_interface(interface):
    interface_ip = get_ip_address(interface)
    mock_socket = make_bound_socket(interface_ip)
    with patch('socket.socket', mock_socket):
        yield


def _join_overrides(d):
    return ['%s=%s' % (k, v) for k, v in d.iteritems()]


def check_if_connected(interface):
    try:
        print "checking interface..."
        get_ip_address(interface)
        print "interface ok!"
    except IOError, e:
        err = "Error! Failed to connect to %s. Reason: %s" % (interface, e)
        return (False, err)
    return (True, None)


def connect_wvdial(port, apn, dial='*99#', wait_connect=5):
    print "connecting wvdial..."
    overrides = {
        'Phone': dial,
        'Init3': 'AT+CGDCONT=1,"IP","%s","",0,0' % apn,
        'Modem': port,
    }
    base_cmd = ['wvdial']
    cmd = base_cmd + _join_overrides(overrides)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(wait_connect)
    return p


def flush_dns():
    print 'flusing dns...'
    print 'dns flushed'
    pass


if __name__ == '__main__':
    port = '/dev/ttyACM0'
    p = connect_wvdial(port, 'http.globe.com.ph')
    print "connected!"
    interface = 'ppp0'
    url = 'http://m.facebook.com'
    print "browsing '%s'" % url
    with use_interface(interface):
        r = requests.get(url, timeout=5)
        inspect = r.text
        print dir(inspect)
        print inspect
    print 'terminating connection'
    p.terminate()
