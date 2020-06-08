#!/usr/bin/env python
"""
treemonger [options] [path]
path:     optional, defaults to PWD
options:  optional
- --exclude-dir=dirname  OR  -d=dirname  # exclude directory by name
- --exclude-file=filename                # exclude file by name
- --exclude-filter=filter                # exclude file by substring match

"""
import sys
import json
import os
import socket
import argparse
from datetime import datetime as dt

from utils import format_bytes
from scan import get_directory_tree, print_directory_tree, tree_to_dict, dict_to_tree
from subdivide import compute_rectangles
# from renderers.tk import render as render_tk
from renderers.tk import render_class

# MAJOR TODOs:
# - text rendering (renderers.tk.TreemongerApp.render_rect()):
#   - make clipping better
#   - scale text to fill rectangle more, so bigger files have bigger text
# - size rectangles by text linecount

# plan
# - scan filesystem and create JSON file with full treemap definition
#   - more or less the same algorithm as before
# - start local server and open html page that handles the interface (very simple)
# - html page loads json file from local server
#   - this is new to me, but very similar to mike bostock d3.js examples

archive_base_path = os.getenv('$HOME') + '/treemonger'

def main(args):
    root, options = parse_args(args)
    print(options)

    save_to_archive = False
    if 'file' in options:
        with open(options['file'], 'r') as f:
            data = json.load(f)
        root = data['root']
        t = dict_to_tree(data['tree'])
        print('loaded scan from file')
        save_to_archive = False
    else:
        t0 = dt.now()
        t = get_directory_tree(
            root,
            exclude_dirs=options['exclude-dirs'],
            exclude_files=options['exclude-files'],
            exclude_filters=options['exclude-filters'],
        )
        t1 = dt.now()

        delta_t = (t1 - t0).seconds + (t1 - t0).microseconds/1e6
        print('%f sec to scan %s / %s files' % (delta_t, format_bytes(t.size), get_total_children(t)))

    if save_to_archive:
        data = {
            'tree': tree_to_dict(t),
            'root': os.path.realpath(root),
            'host': os.getenv('MACHINE', socket.gethostname()),
            'options': options,
        }

        now = dt.strftime(dt.now(), '%Y%m%d-%H%M%S')
        archive_basename = data['root'][1:].replace('/', '-') + '-' + now
        archive_path = archive_base_path + '/' + data['host']
        archive_filename = archive_path + '/' + archive_basename
        print('archiving results to:\n  %s' % archive_filename)
        try:
            if not os.path.exists(archive_path):
                os.mkdir(archive_path)
            with open(archive_filename, 'w') as f:
                json.dump(data, f)
        except Exception as exc:
            print(exc)


    # print(jsonpickle.encode(t))
    # print_directory_tree(t)
    # rects = compute_rectangles(t, [0, width], [0, height])
    # render_tk(rects, width, height, title=os.path.realpath(root))
    # render_class(rects, width, height, title=os.path.realpath(root))

    # import ipdb; ipdb.set_trace

    title = os.path.realpath(root)
    render_class(t, compute_rectangles, title=title)


def get_total_children(t):
    if t.children:
        return sum([get_total_children(c) for c in t.children])
    else:
        return 1


def parse_args(args):
    root = '.'
    flags = []
    options = {
        'exclude-dirs': [],
        'exclude-files': [],
        'exclude-filters': [],
    }
    if len(args) == 1:
        print('using pwd')
    else:
        for arg in args[1:]:
            if arg.startswith('-'):
                flags.append(arg)
                if arg.startswith('--exclude-dir=') or arg.startswith('-d='):
                    options['exclude-dirs'].append(arg.split('=')[1])
                if arg.startswith('--exclude-file='):
                    options['exclude-files'].append(arg.split('=')[1])
                if arg.startswith('--exclude-filter='):
                    options['exclude-filters'].append(arg.split('=')[1])
                if arg.startswith('--file') or arg.startswith('-f='):
                    options['file'] = os.path.expanduser(arg.split('=')[1])
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
