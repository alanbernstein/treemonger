import os
try:
    import magic
    _use_magic = True
except:
    print('magic not available, try:')
    print('  `brew install libmagic` and `pip3 install python-magic` (mac)')
    print('  `sudo apt-get install libmagic1` and `pip3 install python-magic` (linux)')
    _use_magic = False

from utils import format_bytes


class TreeNode(object):
    def __init__(self, path, size=0):
        self.path = path
        self.size = size
        self.children = []
        self.details = {}

    @property
    def name(self):
        name = os.path.basename(self.path)
        try:
            if os.path.isdir(self.path.encode('utf8')):
                name += os.sep
        except UnicodeDecodeError as exc:
            print(exc)
            import ipdb
            ipdb.set_trace()

        return name

    def __str__(self):
        size = format_bytes(self.size)
        info_list = [size]
        if self.children:
            children = '%d children' % len(self.children)
            info_list.append(children)

        if 'lines' in self.details:
            details = '%d lines' % self.details['lines']
            info_list.append(details)

        info = ', '.join(info_list)
        return '<%s: %s>' % (self.name, info)

    def __repr__(self):
        return self.__str__()


def print_directory_tree(t, L=0, max=3):
    """print to stdout"""
    if L < max:
        print('%s%s' % ('  ' * L, t))
        if os.path.isdir(t.path):
            for child in t.children:
                print_directory_tree(child, L + 1)


def tree_to_dict(t):
    return {
        'path': t.path,
        'size': t.size,
        'details': t.details,
        'children': [tree_to_dict(c) for c in t.children],
    }


def dict_to_tree(d):
    t = TreeNode(d['path'], d['size'])
    t.details = d['details']
    t.children = [dict_to_tree(c) for c in d['children']]
    return t


def get_directory_tree(path,
                       exclude_dirs=[],
                       exclude_files=[],
                       exclude_filters=[],
                       skip_mount=False,
                       slow_details=False):
    realpath = os.path.realpath(path)
    base = os.path.basename(path)
    t = TreeNode(path)
    size = 0

    if os.path.islink(path):
        # symlink
        t.details['skip'] = 'symlink'
        return t

    if realpath == '/System/Volumes/Data':
        # hardcoding this because I don't know how to detect it
        print('skip macOS data volume secret link %s' % path)
        t.details['skip'] = 'volume'
        return t

    if skip_mount and not (realpath == '/') and os.path.ismount(realpath):
        # different filesystem, probably don't want to scan
        print('skip mount %s' % path)
        t.details['skip'] = 'mount'
        return t

    elif os.path.isdir(path):
        # directory
        if base in exclude_dirs:
            t.details['skip'] = 'exclude_dir'
            return t
        try:
            files = os.listdir(path)
        except Exception as exc:
            t.details['skip'] = str(exc)
            # exc.errno = 13
            # exc.filename = /usr/sbin/authserver'
            # exc.strerror = 'Permission denied'
            if 'Library' in path:
                # probably an apple permission error, don't need to print each one
                # TODO: accumulate the errors and print a count
                # examples:
                # [Errno 1] Operation not permitted: './System/Volumes/Data/private/var/networkd/db'
                # [Errno 13] Permission denied: './System/Volumes/Data/private/var/install'
                pass
            else:
                print('skipping %s' % (exc))
            return t

        for file in files:
            skip = False
            for filt in exclude_filters:
                if filt in file:
                    skip = True
                    break
            if skip:
                continue
            if file in exclude_files:
                continue
            subtree = get_directory_tree(
                path + os.sep + file, exclude_dirs, exclude_files, exclude_filters)
            if subtree:
                t.children.append(subtree)
                size += t.children[-1].size

    elif os.path.isfile(path):
        # file
        size = os.path.getsize(path)
        if slow_details:
            t.details = get_file_details(path)

    t.size = size
    return t


def get_file_details(path):
    details = {}
    if _use_magic:
        ftype = magic.from_file(path).lower()
        if 'ascii' in ftype:
            details['lines'] = get_line_count(path)

    return details


def get_line_count(path):
    with open(path, 'r') as f:
        content = f.readlines()
    return len(content)


if __name__ == '__main__':
    py_path = os.getenv('PY')
    t = get_directory_tree(py_path)
    print_directory_tree(t)


########################################
# deprecated
def print_treemap_dict(t, L=0, max=3, printfiles=True):
    # prints a formatted list as returned by gettree

    if L < max:
        name = os.path.basename(t['path'])

        if os.path.isdir(t['path']):
            name += os.sep

        print('%s%s: %s' % ('  ' * L, name, t['bytes']))

        if os.path.isdir(t['path']):
            for child in t['children']:
                print_treemap_dict(child, L + 1)


def get_treemap_dict(path):
    t = {'path': path,
         'bytes': 0}

    if os.path.islink(path):
        return t

    bytes = 0
    if os.path.isdir(path):
        try:
            t['children'] = []
            # for file in scandir(path)  # TODO: use this - http://benhoyt.com/writings/scandir/
            for file in os.listdir(path):
                t['children'].append(
                    get_treemap_dict(path + os.path.sep + file))
                bytes += t['children'][-1]['bytes']
        except OSError as exc:
            print('ignoring OSError at %s' % path)

    elif os.path.isfile(path):
        bytes = os.path.getsize(path)

    t['bytes'] = bytes
    return t
