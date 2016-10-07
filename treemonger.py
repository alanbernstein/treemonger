#!/usr/local/bin/python
import sys
import os
import socket

from scan import get_directory_tree, print_directory_tree, tree_to_dict
from subdivide import compute_rectangles
from renderers.tk import render as render_tk

# plan
# - scan filesystem and create JSON file with full treemap definition
#   - more or less the same algorithm as before
# - start local server and open html page that handles the interface (very simple)
# - html page loads json file from local server
#   - this is new to me, but very similar to mike bostock d3.js examples


def main(args):
    if len(args) < 2:
        print('using pwd')
        root = '.'
    else:
        root = args[1]

    t = get_directory_tree(root)

    data = {'tree': tree_to_dict(t),
            'root': os.path.realpath(root),
            'host': os.getenv('MACHINE', socket.gethostname())}
    # pprint(data)
    # print(jsonpickle.encode(t))
    # print_directory_tree(t)

    width = 800
    height = 600
    rects = compute_rectangles(t, [0, width], [0, height])
    render_tk(rects, width, height, title=os.path.realpath(root))


if __name__ == '__main__':
    main(sys.argv)
