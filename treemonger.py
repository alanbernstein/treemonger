#!/usr/local/bin/python
import sys
import os
import socket
import argparse
from collections import defaultdict

from scan import get_directory_tree, print_directory_tree, tree_to_dict
from subdivide import compute_rectangles
#from renderers.tk import render as render_tk
from renderers.tk import render_class

# plan
# - scan filesystem and create JSON file with full treemap definition
#   - more or less the same algorithm as before
# - start local server and open html page that handles the interface (very simple)
# - html page loads json file from local server
#   - this is new to me, but very similar to mike bostock d3.js examples


def main(args):
    root, options = parse_args(args)
    print(options)
    t = get_directory_tree(root, exclude_dirs=options['exclude-dirs'])

    data = {'tree': tree_to_dict(t),
            'root': os.path.realpath(root),
            'host': os.getenv('MACHINE', socket.gethostname())}
    # pprint(data)
    # print(jsonpickle.encode(t))
    # print_directory_tree(t)

    width = 800
    height = 600
    # rects = compute_rectangles(t, [0, width], [0, height])
    # render_tk(rects, width, height, title=os.path.realpath(root))
    # render_class(rects, width, height, title=os.path.realpath(root))

    render_class(t, compute_rectangles, width, height, title=os.path.realpath(root))


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
