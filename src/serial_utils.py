from serial.tools import list_ports


# Port descriptors
DESCRIPTORS = [
    'usbmodem',
    'acm',
    'com',
]

# Modem Baudrate
BAUDRATE = 115200


def detect_ports():
    """Returns all the available ports."""
    devices = []
    for p in list_ports.comports():
        for d in DESCRIPTORS:
            if d in p.device.lower():
                _in = p.hwid
                devices.append(p.device)
    return devices


def clean_lines(lines):
    """Strips away any instances of \r or \n at the end of
    the line strings. Also removes empty lines."""
    _lines = []
    for l in lines:
        l = l.strip().rstrip()
        if len(l) > 0:
            _lines.append(l)
    return _lines
