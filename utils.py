import os
import platform
import subprocess

_abbrevs = [(1 << 50, 'P'),
            (1 << 40, 'T'),
            (1 << 30, 'G'),
            (1 << 20, 'M'),
            (1 << 10, 'k'),
            (1, '')
            ]


def format_bytes(size):
    """Return a human readable size string (i.e., kB, MB, etc)"""
    k = 2.0
    # this makes the jump occur at 2kB instead of 1kB, which makes things a little more readable
    for factor, prefix in _abbrevs:
        if size > k * factor:
            break
    # return `int(size/(1.0*factor))` + suffix
    s = "%.2f%sB" % (size / (1.0 * factor), prefix)
    return s


def reverse_path(p):
    parts = p.split(os.path.sep)
    return os.path.sep.join(parts[::-1])


def open_file(path):
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def shorten(string, dx, text_size):
    """ should shorten a string to fit in length diff(xlim) pixels """
    # http://stackoverflow.com/questions/1123463/clipping-text-in-python-tkinter

    if (len(string)-5) * text_size > dx:
        newLen = int(dx / text_size + 5)
        string = string[0:newLen - 1]

    return string


def format_combo(combo):
    """Format a key combo tuple into a readable string."""
    parts = list(combo)
    return '+'.join(parts)