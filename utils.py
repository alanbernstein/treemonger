import os

_abbrevs = [(1 << 50, 'P'),
            (1 << 40, 'T'),
            (1 << 30, 'G'),
            (1 << 20, 'M'),
            (1 << 10, 'k'),
            (1, '')
            ]


def format_bytes(size):
    """Return a string representing the metric suffix of a size"""
    for factor, suffix in _abbrevs:
        if size > factor:
            break
    # return `int(size/(1.0*factor))` + suffix
    s = "%.2f%s" % (size / (1.0 * factor), suffix)
    return s


def reverse_path(p):
    parts = p.split(os.path.sep)
    return os.path.sep.join(parts[::-1])
