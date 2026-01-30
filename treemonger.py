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
import argparse
import datetime
from datetime import datetime as dt
import glob
import json
import os
import pathlib
import socket
import sys

from logger import logger, set_verbosity
from utils import format_bytes
from scan import get_directory_tree, print_directory_tree, tree_to_dict, dict_to_tree
from subdivide import compute_rectangles
from renderers.tk import init_app

from ipdb import iex

# MAJOR TODOs:
# - text rendering (renderers.tk.TreemongerApp.render_rect()):
#   - make clipping better
#   - scale text to fill rectangle more, so bigger files have bigger text
# - size rectangles by text linecount
# - "restore this file" after moving to trash
# - undo move-to-trash actions
# - show hover info in status bar
# - highlight specific filetype, file extension
# - use modern logging system, with colored loglevels
# - move UI hints to the UI instead of the terminal logs

# make --exclude-dirs work with --file (need to filter before render, rather than during scan)

# plan
# - scan filesystem and create JSON file with full treemap definition
#   - more or less the same algorithm as before
# - start local server and open html page that handles the interface (very simple)
# - html page loads json file from local server (e.g. bostock examples)

# color options
# 1. depth -> color
# 2. type -> color
# 3. depth -> saturation, type -> hue


config_file_path = os.path.expanduser('~/.config/treemonger.json')
if not os.path.exists(config_file_path):
    script_path = str(pathlib.Path(__file__).parent.resolve())
    config_file_path = script_path + '/config.json'

NOW = dt.strftime(dt.now(), '%Y%m%d-%H%M%S')
HOST = os.getenv('MACHINE', socket.gethostname())

@iex
def main(args):
    # TODO: refactor into class so archive_path etc can be shared
    config = parse_config()
    config_file_flags = config['flags']

    root, cli_flags = parse_args(args)
    logger.info(f"cli flags: {cli_flags}")
    flags = config_file_flags

    # update list values by combining rather than replacing
    for k, v in cli_flags.items():
        if cli_flags.get(k, []) == []:
            continue
        if type(v) is list:
            flags[k].extend(cli_flags[k])
        else:
            flags[k] = cli_flags[k]

    logger.info(f"full flags: {flags}")
    flags_str = '\n'.join([f'  {k}: {v}' for k, v in flags.items()])

    set_verbosity(cli_flags.get("verbosity", 0))

    logger.debug(f"full_flags:\n{flags_str}")
    # logger.debug(f"full flags: %s" % json.dumps(flags, indent=2))


    if 'file' in flags:
        
        def scan_func():
            with open(flags['file'], 'r') as f:
                data = json.load(f)
            root = data['root']
            t = dict_to_tree(data['tree'])
            logger.info(f'loaded scan from file "{flags['file']}"')
            save_to_archive = False
            return t
    else:
        def scan_func():
            t0 = dt.now()
            t = get_directory_tree(
                root,
                exclude_dirs=flags['exclude-dirs'],
                exclude_files=flags['exclude-files'],
                exclude_filters=flags['exclude-filters'],
                skip_mount=flags['skip-mount'],
            )
            t1 = dt.now()

            delta_t = (t1 - t0).seconds + (t1 - t0).microseconds/1e6
            logger.info('%f sec to scan %s / %s files' %
                (delta_t, format_bytes(t.size), get_total_children(t)))
            return t

    realroot = os.path.realpath(root)
    archive_filename = get_archive_location(flags, realroot, HOST, NOW)
    archive_path = os.path.dirname(archive_filename)

    if flags.get('file-latest', False):
        fname = get_latest_file_for_pwd(archive_path)
        ts = os.stat(fname).st_mtime
        ts_dt = datetime.datetime.fromtimestamp(ts)
        ts_str = ts_dt.strftime('%Y-%m-%d %H:%M:%S')

        logger.info('using latest recorded file (%s): %s' % (ts_str, fname))
        flags['file'] = fname

    logger.info('skipping archive during refactor')
    # if not config.flags.get('file', False) and config.flags['save-to-archive']:
    #     data = {
    #         'tree': tree_to_dict(t),
    #         'root': realroot,
    #         'host': HOST,
    #         'options': flags,
    #         'scan_timestamp': NOW,
    #         'scan_duration_seconds': delta_t,
    #     }

    #     logger.info('archiving results to:\n  %s' % archive_filename)
    #     try:
    #         if not os.path.exists(archive_path):
    #             os.mkdir(archive_path)
    #         with open(archive_filename, 'w') as f:
    #             json.dump(data, f)
    #     except Exception as exc:
    #         logger.error(exc)

    config["trash-log-file"] = get_trashlog_location(flags, realroot, HOST, NOW)
    trash_path = os.path.dirname(config["trash-log-file"])
    os.makedirs(trash_path, exist_ok=True)


    title = os.path.realpath(root)
    init_app(scan_func, compute_rectangles, config, title=title)


def get_archive_location(flags, rootpath, host, timestamp):
    if rootpath == '/':
        # prevent clobber
        rootpath = 'root'
    rootpath_slug = rootpath[1:].replace('/', '-')
    pattern = flags.get('archive-name-pattern', '')
    if pattern:
        archive_basename = pattern
        archive_basename = archive_basename.replace('%host', HOST)
        archive_basename = archive_basename.replace('%root', rootpath_slug)
        archive_basename = archive_basename.replace('%timestamp', NOW)
    else:
        return ''

    archive_filename = '%s/%s' % (
        os.path.expanduser(flags['archive-base-path']),
        archive_basename,
    )
    return archive_filename

def get_trashlog_location(flags, rootpath, host, timestamp):
    # TODO consolidate this with get_archive_location
    if rootpath == '/':
        # prevent clobber
        rootpath = 'root'
    rootpath_slug = rootpath[1:].replace('/', '-')
    pattern = flags.get('trash-log-pattern', '')
    if pattern:
        trashlog_file = pattern
        trashlog_file = trashlog_file.replace('%host', HOST)
        trashlog_file = trashlog_file.replace('%root', rootpath_slug)
        trashlog_file = trashlog_file.replace('%timestamp', NOW)
        trashlog_file = os.path.expanduser(trashlog_file)
    else:
        return ''

    return trashlog_file

def get_total_children(t):
    if t.children:
        return sum([get_total_children(c) for c in t.children])
    else:
        return 1


def parse_config():
    logger.info('loading config from %s' % config_file_path)
    with open(config_file_path) as f:
        config = json.load(f)
    return config


def parse_args(args):
    root = '.'
    flags = []
    cli_flags = {
        'exclude-dirs': [],
        'exclude-files': [],
        'exclude-filters': [],
    }

    if len(args) == 1:
        logger.info('scanning pwd (%s)' % os.path.realpath(root))
        return root, cli_flags

    for arg in args[1:]:
        if arg.startswith('-'):
            flags.append(arg)
            if arg.startswith('--exclude-dir=') or arg.startswith('-d='):
                cli_flags['exclude-dirs'].append(arg.split('=')[1])
            if arg.startswith('--exclude-file='):
                cli_flags['exclude-files'].append(arg.split('=')[1])
            if arg.startswith('--exclude-filter='):
                cli_flags['exclude-filters'].append(arg.split('=')[1])
            if arg.startswith('--file') or arg.startswith('-f'):
                if '=' in arg:
                    cli_flags['file'] = os.path.expanduser(arg.split('=')[1])
                else:
                    cli_flags['file-latest'] = True
                    logger.debug('set file-latest = true')
            if arg.startswith('--skip-mount') or arg == '-x':
                if 'false' in arg.lower():
                    cli_flags['skip-mount'] = False
                else:
                    cli_flags['skip-mount'] = True
            if arg == '-v':
                cli_flags['verbosity'] = 1
            if arg == '-vv':
                cli_flags['verbosity'] = 2

        else:
            root = arg.rstrip('/')
    
    logger.info(f"flags: {cli_flags}")

    return root, cli_flags


def get_latest_file_for_pwd(archive_path):
    glb = glob.glob(archive_path + '/*')
    if glb:
        files_ages = [(x, os.stat(x).st_mtime) for x in glb]
        files_ages.sort(key=lambda x: -x[1])
        return files_ages[0][0]

    return ''


if __name__ == '__main__':
    # TODO: use argparse
    if False:
        parser = argparse.ArgumentParser()
        parser.add_argument('root', type=str, default='.')
        parser.add_argument('-d', '--exclude-dir', default=[])
        args = parser.parse_args()
        print(args)

    main(sys.argv)
