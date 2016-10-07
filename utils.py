import os

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
    # this makes the jump occur at 2kB instead of 1kB, which makes thing a little more readable
    for factor, suffix in _abbrevs:
        if size > k * factor:
            break
    # return `int(size/(1.0*factor))` + suffix
    s = "%.2f%sB" % (size / (1.0 * factor), suffix)
    return s


def reverse_path(p):
    parts = p.split(os.path.sep)
    return os.path.sep.join(parts[::-1])
