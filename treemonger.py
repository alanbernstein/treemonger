#!/usr/local/bin/python
import sys
import os
import socket
import argparse
from datetime import datetime as dt
from collections import defaultdict

from utils import format_bytes
from scan import get_directory_tree, print_directory_tree, tree_to_dict
from subdivide import compute_rectangles
#from renderers.tk import render as render_tk
from renderers.tk import render_class

# MAJOR TODOs:
# - fix text placement
# - switch out the ~/cmd/treemonger link to this one

# plan
# - scan filesystem and create JSON file with full treemap definition
#   - more or less the same algorithm as before
# - start local server and open html page that handles the interface (very simple)
# - html page loads json file from local server
#   - this is new to me, but very similar to mike bostock d3.js examples


def main(args):
    root, options = parse_args(args)
    print(options)

    t0 = dt.now()
    t = get_directory_tree(root, exclude_dirs=options['exclude-dirs'])
    t1 = dt.now()

    delta_t = (t1 - t0).seconds + (t1 - t0).microseconds/1e6
    print('%f sec to scan %s / %s files' % (delta_t, format_bytes(t.size), get_total_children(t)))

    data = {'tree': tree_to_dict(t),
            'root': os.path.realpath(root),
            'host': os.getenv('MACHINE', socket.gethostname())}
    # pprint(data)
    # print(jsonpickle.encode(t))
    # print_directory_tree(t)
    # rects = compute_rectangles(t, [0, width], [0, height])
    # render_tk(rects, width, height, title=os.path.realpath(root))
    # render_class(rects, width, height, title=os.path.realpath(root))

    render_class(t, compute_rectangles, title=os.path.realpath(root))


def get_total_children(t):
    if t.children:
        return sum([get_total_children(c) for c in t.children])
    else:
        return 1


def parse_args(args):
    root = '.'
    flags = []
    options = {'exclude-dirs': []}
    if len(args) == 1:
        print('using pwd')
    else:
        for arg in args[1:]:
            if arg.startswith('-'):
                flags.append(arg)
                if arg.startswith('--exclude-dir=') or arg.startswith('-d='):
                    options['exclude-dirs'].append(arg.split('=')[1])
            else:
                root = arg

    return root, options


if __name__ == '__main__':
    # TODO: use argparse
    if False:
        parser = argparse.ArgumentParser()
        parser.add_argument('root', type=str, default='.')
        parser.add_argument('-d', '--exclude-dir', default=[])
        args = parser.parse_args()
        print(args)


    main(sys.argv)
