import glob
import os.path


def get_modems():
    """Returns a list of modems."""
    modems = []
    for f in glob.glob('/dev/ttyACM*'):
        modems.append(f)
    return modems
