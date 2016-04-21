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


if __name__ == '__main__':
    interface = 'wlan0'
    url = 'http://m.facebook.com'
    with use_interface(interface):
        r = requests.get(url)
        inspect = r.text
        print dir(inspect)
        print inspect
