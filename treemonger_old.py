#!/usr/local/bin/python
# tree.py
# run with:
#   python tree.py PATH
#
#
# https://github.com/benhoyt/scandir os.walk replacement
#
#
# proof of concept treemapper
# print directory tree structure with sizes
#  seems to work well.. but how will it stand up to a larger directory structure..?
#
# original treemap article: http://hcil.cs.umd.edu/trs/91-03/91-03.html
#
# maybe this to handle UI instead of rolling my own?
# http://matplotlib.org/users/event_handling.html
#
# first version finished 2012/11/30

# todo
# - keypresses:
#   'q': quit
#   'r': refresh
# - click handling
#   - zoom
#   - print full path to clicked file
#     - then 'd' in CLI to delete, 'o' to open, 'i' for info, etc
#
#
# rewrite with actual design
# - structure
#   - walk filesystem and get data
#   - handle the treemapping division algorithm
#   - handle the treemapping layout algorithm  (i think these are too intertwined to be separated)
#     - https://github.com/laserson/squarify for inspiration - then use similar interface to steal examples of making it interactive
#   - application class to deal with tk
# - redo GUI
#   - SVG ala flame graph? (uses SMIL which was deprecated in chrome 2015, prefer something more future proof)
#     - related but different: http://tympanus.net/codrops/2014/08/19/making-svgs-responsive-with-css/
#     - http://stackoverflow.com/questions/30965580/deprecated-smil-svg-animation-replaced-with-css-or-web-animations-effects-hover
#     - https://github.com/webframes/smil2css
#     - check up on flamegraph in a while and see if they've figured out an alternative - https://github.com/brendangregg/FlameGraph
#   - js somehow... dont really want to use a pure js library because of the volume of data that is fundamentally local...
#   - some more modern, native python gui lib
#     - bokeh
#       - interactive, modern, intended for use with large/streaming data sets
#       - good opportunity to make the layout algorithm capable of dynamic/updating
#       - not obvious how to do a treemap or generally custom plot
#     - vincent - "data processing of python, visualization of js"
#       - not obvious how to do treemaps directly
#   - d3.js
#
# after doing all the research for the above block of comments 2016/06/17, i still don't see an obvious
# way to write a simple plugin or class that will easily get me an interactive treemap.
# guess ill have to either stick with minimally interactive, or write it all from scratch myself somehow.
# if im going to do that, might be good to figure out how to do it in javascript one way or another - get help from ben/sean/cina
#
# OR - just output json, and send it to a d3-based js page
# https://bost.ocks.org/mike/treemap/
# https://bl.ocks.org/mbostock/4063582
# http://bl.ocks.org/ganeshv/6a8e9ada3ab7f2d88022
# http://www.billdwhite.com/wordpress/2012/12/16/d3-treemap-with-title-headers/

# faster walk: http://benhoyt.com/writings/scandir/


import os
import sys
from os import listdir, sep
from os.path import abspath, basename, isdir, isfile, islink, getsize, join
from sys import argv
import Tkinter as tk
from pprint import pprint
from numpy import sign

from panda.debug import debug, pm, pp


def ScanCallback():
    print ScanEntry.get()


def gettree(path):
    # returns a list t with elements
    # [path size child1 child2 ...]
    # each child is a similar list

    t = [path, 0]

    if islink(path):  # want symlinks to have 0 size
        return t

    size = 0
    if isdir(path):
        try:
            for file in listdir(path):
                t.append(gettree(path + sep + file))
                size = size + t[-1][1]
        except OSError as exc:
            # this can be caused by filesystem errors that i don't know how to fix in linux
            # eg, broken file with no corresponding inode
            print('ignoring OSError at %s' % path)
    elif isfile(path):
        size = getsize(path)

    t[1] = size
    return t


def printtree(t, L=0, max=3, printfiles=True):
    # prints a formatted list as returned by gettree

    if L < max:
        if isdir(t[0]):
            print ' ' * L + basename(t[0]) + "/: " + str(t[1])
        if isfile(t[0]) & printfiles:
            print ' ' * L + basename(t[0]) + ": " + str(t[1])

        if isdir(t[0]):
            for i in range(2, len(t)):
                printtree(t[i], L + 1)

# color options
# 1. depth -> color
# 2. type -> color
# 3. depth -> saturation, type -> hue

# spacemonger color scheme
# hue    main           light          dark
# red    (255,127,127), (255,191,191), (191,127,127)
# orange (255,191,127), (255,223,191), (191,159,95)
# yellow (255,255,000), (255,255,191), (191,191,63)
# green  (127,255,127), (191,255,191), (127,191,127)
# cyan   (127,255,255), (223,255,255), (127,191,191)
# blue   (191,191,255), (223,223,255), (159,159,255)
# gray   (191,191,191), (223,223,223), (159,159,159)
# pink   (255,127,255), (255,191,255), (191,127,191)
#
# 255 223 191 159 127 95 63
#  ff  df  bf  9f  7f 5f 3f
colors = ["#ff7f7f", "#ffbf7f", "#ffff00", "#7fff7f",
          "#7fffff", "#bfbfff", "#bfbfbf", "#ff7fff"]
colors_light = ["#ffbfbf", "#ffdfbf", "#ffffbf", "#bfffbf",
                "#dfffff", "#dfdfff", "#dfdfdf", "#ffbfff"]
colors_dark = ["#bf7f7f", "#bf9f5f", "#bfbf3f", "#7fbf7f",
               "#7fbfbf", "#9f9fff", "#9f9f9f", "#bf7fbf"]

text_offset_x = 3
text_offset_y = 3
dir_text_offset = 6
xpad = 0
ypad = 0
min_box_size = 10
max_filesystem_depth = 16


def drawtree(t, canv, xlim, ylim, recurse_level=0, dir_level=0):
    # this function has to handle 3 cases:
    #  - single file: draw a 'file box' and label it if big enough
    #  - full directory: draw 'directory box' and label it; divide and recurse
    #  - file group: DONT draw anything, just divide and recurse
    #
    # t = [path size child1 child2 ...]

    # print ' '*recurse_level + t[0]

    if (dir_level > max_filesystem_depth or
            xlim[1] - xlim[0] < min_box_size or
            ylim[1] - ylim[0] < min_box_size):
        # print "maxdepth reached"
        # pprint(t)
        return

    subdir_flag = 0

    if t[0] != '-':
        # either a single file or a directory - NOT a 'file group'
        # - draw a box and text
        # - if directory, compute new padded bounds for child boxes

        ul = (xlim[0] + 1, ylim[0] + 1)
        ur = (xlim[1] + 1, ylim[0] + 1)
        ll = (xlim[0] + 1, ylim[1] + 1)
        lr = (xlim[1] + 1, ylim[1] + 1)

        color_index = min(dir_level, 7)  # todo: make this cycle instead
        # color_index = dir_level

        r = canv.create_rectangle(ul[0], ul[1], lr[0], lr[1], width=1,
                                  fill=colors[color_index], outline='black')

        canv.create_line(ll[0] + 1, ll[1] - 1, ul[0] + 1, ul[1] + 1, ur[0] - 1, ur[1] + 1,
                         fill=colors_light[color_index])
        canv.create_line(ll[0] + 1, ll[1] - 1, lr[0] - 1, lr[1] - 1, ur[0] - 1, ur[1] + 1,
                         fill=colors_dark[color_index])

        if isdir(t[0]):
            txt = t[0] if recurse_level == 0 else basename(t[0])
            txt = txt + " (" + metric(t[1]) + ")"
            txt = shorten(txt, xlim)
            canv.create_text(xlim[0] + text_offset_x, ylim[0] + text_offset_y,
                             text=txt, fill="black", anchor=tk.NW, font=("Helvectica", textSize))

            # print "directory: drawing box"
            subdir_flag = 1

            ylim[0] = ylim[0] + textSize + dir_text_offset
            ylim[1] = ylim[1] - 3
            xlim[0] = xlim[0] + 3
            xlim[1] = xlim[1] - 3

        else:
            txt = t[0] if recurse_level == 0 else basename(t[0])
            txt = txt + " (" + metric(t[1]) + ")"
            txt = shorten(txt, xlim)
            canv.create_text(xlim[0] / 2 + xlim[1] / 2, ylim[0] / 2 + ylim[1] / 2,
                             text=txt, fill="black", anchor=tk.CENTER, font=("Helvectica", textSize))

            # print "single file: drawing box"
            # endif
        # endif

    if len(t) > 2:
        # directory or file group
        # divide children into two nearly equal parts,
        # call drawtree on both halves
        # print "directory or file group; splitting and recursing"

        # def compute_halves(t,xlim,ylim)
        #     return groupA, groupB, xA, yA, xB, yB

        # find approximate halfway point for division
        name = t[0]
        totalSize = t[1]
        Asize = 0
        t = t[2:]
        # print('???')
        # pprint(t)
        t.sort(filecompare)
        # t.sort(key=lambda x: x[1])
        divpoint = 0
        while Asize < totalSize / 2:
            Asize = Asize + t[divpoint][1]
            divpoint = divpoint + 1
        if divpoint == len(t):
            divpoint = divpoint - 1
            Asize = Asize - t[divpoint][1]

        Bsize = totalSize - Asize

        # split into two groups, append extra information
        groupA = t[0:divpoint]
        groupB = t[divpoint:]

        groupA.insert(0, Asize)  # insert correct filegroup size
        # this is the name - means not a real directory but rather a filegroup
        groupA.insert(0, '-')
        groupB.insert(0, Bsize)  # insert correct filegroup size
        # this is the name - means not a real directory but rather a filegroup
        groupB.insert(0, '-')

        # figure out geometric division
        if xlim[1] - xlim[0] > ylim[1] - ylim[0]:  # wide box - divide left/right
            xdiv = xlim[0] + (xlim[1] - xlim[0]) * Asize / totalSize
            xA = [xlim[0], xdiv]
            xB = [xdiv, xlim[1]]
            yA = ylim
            yB = ylim
        else:  # tall box - divide top/bottom
            ydiv = ylim[0] + (ylim[1] - ylim[0]) * Asize / totalSize
            xA = xlim
            xB = xlim
            yA = [ylim[0], ydiv]
            yB = [ydiv, ylim[1]]

        # extract single element if necessary; add some graphical padding
        if len(groupA) == 3:
            groupA = groupA[2]
            xA = [xA[0] + xpad, xA[1] - xpad]
            yA = [yA[0] + ypad, yA[1] - ypad]
        if len(groupB) == 3:
            groupB = groupB[2]
            xB = [xB[0] + xpad, xB[1] - xpad]
            yB = [yB[0] + ypad, yB[1] - ypad]
    # end compute_halves

        # recurse
        drawtree(groupA, canv, xA, yA, recurse_level +
                 1, dir_level + subdir_flag)
        drawtree(groupB, canv, xB, yB, recurse_level +
                 1, dir_level + subdir_flag)


def filecompare(A, B):
    # comparison operator for use in sorting list of files
    # return A[1] == B[1]
    # return int(sign(A[1] - B[1]))
    return 1 if A[1] > B[1] else -1


_abbrevs = [
    (1 << 50L, 'P'),
    (1 << 40L, 'T'),
    (1 << 30L, 'G'),
    (1 << 20L, 'M'),
    (1 << 10L, 'k'),
    (1, '')
]


def metric(size):
    """Return a string representing the metric suffix of a size"""
    for factor, suffix in _abbrevs:
        if size > factor:
            break
    # return `int(size/(1.0*factor))` + suffix
    s = "%.2f%s" % (size / (1.0 * factor), suffix)
    return s


def shorten(string, xlim):
    """ should shorten a string to fit in length diff(xlim) pixels """
    # http://stackoverflow.com/questions/1123463/clipping-text-in-python-tkinter

    if len(string) * textSize - 5 * textSize > xlim[1] - xlim[0]:
        newLen = (xlim[1] - xlim[0]) / textSize + 5
        string = string[0:newLen - 1]

    return string


def on_resize(ev):
    # canv.coords(line,0,0,ev.width,ev.height)
    print('resized: %d %d' % (ev.width, ev.height))
    # pprint(vars(ev))
    canv.coords(rect1, 1, 1, ev.width - 2, ev.height - 2)
    drawtree(t, canv, [3, ev.width - 4], [3, ev.height - 4])


def on_click1(ev):
    print('left clicked: (%d, %d), (%d, %d)' %
          (ev.x, ev.y, ev.x_root, ev.y_root))
    print('not yet implemented: zoom in')
    # pprint(vars(ev))


def on_click2(ev):
    print('middle clicked: (%d, %d), (%d, %d)' %
          (ev.x, ev.y, ev.x_root, ev.y_root))
    # pprint(vars(ev))


def on_click3(ev):
    print('right clicked: (%d, %d), (%d, %d)' %
          (ev.x, ev.y, ev.x_root, ev.y_root))
    # pprint(vars(ev))


def on_click4(ev):
    print('scrolled up')
    # pprint(vars(ev))


def on_click5(ev):
    print('scrolled down')
    # pprint(vars(ev))


def on_keydown(ev):
    print('keydown: %s' % ev.char)
    # pprint(vars(ev))


def on_keyup(ev):
    print('keyup: %s' % ev.char)
    if ev.char == 'q':
        exit()
    if ev.char == 'r':
        # pprint(vars(ev))
        # drawtree(t, canv, [3, int(ev.width)-4], [3, int(ev.height)-4])
        print('not yet implemented: refresh')
        # requires OOP redesign or global variable
    if ev.char == 'u':
        print('not yet implemented: go up in the directory tree')
    if ev.keysym == 'Up':
        print('not yet implemented: navigate up in map')
    if ev.keysym == 'Down':
        print('not yet implemented: navigate down in map')
    if ev.keysym == 'Right':
        print('not yet implemented: navigate right in map')
    if ev.keysym == 'Left':
        print('not yet implemented: navigate left in map')


def reverse_path(p):
    parts = p.split(os.path.sep)
    return os.path.sep.join(parts[::-1])


# def main():
# setup window and canvas

global ScanEntry, textSize
textSize = 8

if len(argv) < 2:
    print('no inputs, using pwd')
    treepath = '.'
else:
    treepath = argv[1]

root = tk.Tk()

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
w = screen_width / 2            # default window width
h = screen_height / 2           # default window height
x = (screen_width / 2) - (w / 2)  # default window x position (centered)
y = (screen_height / 2) - (h / 2)  # default window y position (centered)
root.geometry('%dx%d+%d+%d' % (w, h, x, y))


root.title('%s' % reverse_path(abspath(treepath)))

# this doesnt seem to work
# icon_fname = 'treemonger-icon.ico'
# icon_fullpath = os.getenv('SRC') + '/py/treemonger/' + icon_fname
# print(os.path.exists(icon_fname))
# root.iconbitmap(bitmap=icon_fname)


# not sure if w and h do anything here
canv = tk.Canvas(root, width=w, height=h, bg='black')
# canv = Canvas(root, bg = 'black')
canv.pack(expand=True, fill=tk.BOTH)  # ?
# canv.grid(row=0, column=0, columnspan=3);
rect1 = canv.create_rectangle(
    0, 0, 0, 0, width=1, fill="white", outline='black')
canv.bind("<Configure>", on_resize)
canv.bind("<Button-1>", on_click1)
canv.bind("<Button-2>", on_click2)
canv.bind("<Button-3>", on_click3)
canv.bind("<Button-4>", on_click4)
canv.bind("<Button-5>", on_click5)
root.bind("<KeyPress>", on_keydown)
root.bind("<KeyRelease>", on_keyup)

# Button(root, text='Quit', command=root.quit).grid(row=1, column=0)
# Button(root, text='Scan', command=ScanCallback).grid(row=1, column=1)
# ScanEntry = Entry(root, width=50)
# ScanEntry.insert(0,'asfasd')
# ScanEntry.grid(row=1, column=2)




# tree stuff
path = abspath(treepath)
t = gettree(path)
# printtree(t)
if isdir(path) & 1:
    drawtree(t, canv, [3, w - 4], [3, h - 4])
    root.mainloop()

else:
    print "input is not a directory ???"


if __name__ == '__main__':  # if executing standalone, call main
    pass
# main()
