import glob
import os.path
import serial
import serial.tools.list_ports


def get_modems():
    """Returns a list of modems."""
    modems = []
    for f in glob.glob('/dev/ttyACM*'):
        modems.append(f)

    # If 'probably', windows
    if not modems:
        modems = [s[0] for s in serial.tools.list_ports.comports()]
    return modems
