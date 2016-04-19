import serial_gsm
import urllib2
import socket
import time


print 'binding socket to ppp0'
ip = serial_gsm.get_ip_address('ppp0')
socket.socket = serial_gsm.make_bound_socket(ip)
print 'socket bound to ip: %s' % ip
print '...'
time.sleep(0.5)
print 'sending request...'
r = urllib2.urlopen('http://m.facebook.com')
print 'request complete.'
print '-----------------------------'
print r.read()
print '-----------------------------'
