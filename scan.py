from os import listdir, sep
from os.path import abspath, basename, isdir, isfile, islink, getsize, join


class TreeNode(object):
    def __init__(self, path, size=0):
        self.path = path
        self.size = size
        self.children = []

    def add_child(self):
        pass

    def get_size(self):
        size = 0
        for node in self.children:
            self


def get_directory_tree(path):
    t = TreeNode(path)

    size = 0
    if islink(path):
        pass
    elif isdir(path):
        for file in listdir(path):
            t.children.append(get_directory_tree(path + sep + file))
            size += t.children[-1].size
    elif isfile(path):
        size = getsize(path)

    t.size = size
    return t


def gettree_old(path):
    # returns a list t with elements
    # [path size child1 child2 ...]
    # each child is a similar list

    t = [path, 0]

    if islink(path):  # want symlinks to have 0 size
        return t

    size = 0
    if isdir(path):
        for file in listdir(path):
            t.append(gettree_old(path + sep + file))
            size = size + t[-1][1]
    elif isfile(path):
        size = getsize(path)

    t[1] = size
    return t
