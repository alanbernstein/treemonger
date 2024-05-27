#!/usr/bin/env python3
"""
treemonger [options] [path]
path:     optional, defaults to PWD
options:  optional
- --exclude-dir=dirname  OR  -d=dirname  # exclude directory by name
- --exclude-file=filename                # exclude file by name
- --exclude-filter=filter                # exclude file by substring match
- --file=pth                             # load previous scan from file
- --file                                 # automatically load most recent scan from PWD


"""
import sys
import json
import os
import socket
import argparse
import pathlib
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

archive_base_path = os.getenv('HOME') + '/treemonger'

config_file_path = os.path.expanduser('~/.config/treemonger.json')
if not os.path.exists(config_file_path):
    script_path = str(pathlib.Path(__file__).parent.resolve())
    config_file_path = script_path + '/config.json'

NOW = dt.strftime(dt.now(), '%Y%m%d-%H%M%S')
HOST = os.getenv('MACHINE', socket.gethostname())

def main(args):
    # TODO: refactor into class so archive_path etc can be shared
    options = {
        'exclude-dirs': [],
        'exclude-files': [],
        'exclude-filters': [],
        'save-to-archive': True,
        'skip-mount': False,
    }

    config_options = parse_config()
    root, arg_options = parse_args(args)

    for k, v in options.items():
        if type(v) is list:
            v.extend(config_options.get(k, []))
            v.extend(arg_options.get(k, []))

    print(options)

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
            skip_mount=options['skip-mount'],
        )
        t1 = dt.now()

        delta_t = (t1 - t0).seconds + (t1 - t0).microseconds/1e6
        print('%f sec to scan %s / %s files' %
              (delta_t, format_bytes(t.size), get_total_children(t)))

    if options['save-to-archive']:
        data = {
            'tree': tree_to_dict(t),
            'root': os.path.realpath(root),
            'host': HOST,
            'options': options,
            'scan_timestamp': NOW,
            'scan_duration_seconds': delta_t,
        }

        if data['root'] == '/':
            # prevent clobber
            data['root'] = 'root'
        archive_basename = data['root'][1:].replace('/', '-') + '-' + NOW
        archive_path = archive_base_path + '/' + HOST
        archive_filename = archive_path + '/' + archive_basename

        # archive_filename = get_archive_filename(data['root'])  # TODO

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
    print('calling render_class')
    render_class(t, compute_rectangles, title=title)


def get_archive_filename(root):
    # TODO move filename logic to here 
    return ''

def get_total_children(t):
    if t.children:
        return sum([get_total_children(c) for c in t.children])
    else:
        return 1


def parse_config():
    with open(config_file_path) as f:
        config = json.load(f)
    return config


def parse_args(args):
    root = '.'
    flags = []
    options = {
        'exclude-dirs': [],
        'exclude-files': [],
        'exclude-filters': [],
    }

    if len(args) == 1:
        print('using pwd (%s)' % os.path.realpath(root))
        return root, options

    for arg in args[1:]:
        if arg.startswith('-'):
            flags.append(arg)
            if arg.startswith('--exclude-dir=') or arg.startswith('-d='):
                options['exclude-dirs'].append(arg.split('=')[1])
            if arg.startswith('--exclude-file='):
                options['exclude-files'].append(arg.split('=')[1])
            if arg.startswith('--exclude-filter='):
                options['exclude-filters'].append(arg.split('=')[1])
            if arg.startswith('--file') or arg.startswith('-f'):
                if '=' in arg:
                    options['file'] = os.path.expanduser(arg.split('=')[1])
                else:
                    fname, age = get_latest_file_for_pwd()
                    print('using latest file (age = %s): %s' % (age, fname))
                    options['file'] = fname
            if arg.startswith('--skip-mount') or arg == '-x':
                options['skip-mount'] = True

        else:
            root = arg

    return root, options


def get_latest_file_for_pwd():
    archive_basename = get_archive_basename()  # TODO use this
    glb = glob.glob(archive_basename)
    if glb:
        files_ages = [(x, os.stat(x).st_mtime) for x in glb]
        files_ages.sort(files_ages, key=lambda x: -x[1])
        return files_ages[0]

    return '', 0


if __name__ == '__main__':
    # TODO: use argparse
    if False:
        parser = argparse.ArgumentParser()
        parser.add_argument('root', type=str, default='.')
        parser.add_argument('-d', '--exclude-dir', default=[])
        args = parser.parse_args()
        print(args)

    main(sys.argv)
