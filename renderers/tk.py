import os
import platform
import subprocess
import sys

try:
    import pyperclip
    pyperclip_present = True
except:
    pyperclip_present = False

import tkinter as tk

from utils import shorten
from .colormap import colormap
from constants import (text_size,
                       text_offset_x,
                       text_offset_y,
                       )


class Demo1:
    def __init__(self, master):
        self.master = master
        self.frame = tk.Frame(self.master)
        self.button1 = tk.Button(self.frame, text='null', width=25, command=self.new_window)
        self.button1.pack()
        self.frame.pack()

    def new_window(self):
        pass


class TreemongerAppOld(object):
    def __init__(self, master, width, height, title, tree=None):
        self.master = master
        self.frame = tk.Frame(self.master)

        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()
        x = (screen_width / 2) - (width / 2)  # default window x position (centered)
        y = (screen_height / 2) - (height / 2)  # default window y position (centered)
        master.geometry('%dx%d+%d+%d' % (width, height, x, y))
        master.title(title)

        self.canv = tk.Canvas(master, bg='black')
        self.canv.pack(expand=True, fill=tk.BOTH)  # ?
        # canv.grid(row=0, column=0, columnspan=3);
        self.root_rect = self.canv.create_rectangle(0, 0, 0, 0, width=1,
                                                    fill="white", outline='black')
        # self.canv.bind("<Configure>", on_resize)

        self.frame.pack()

    def add_data(self, rects):
        self.rects = rects

    def render(self):
        # TODO: these values should be normalized
        # but the subdivision depends on the aspect ratio
        # so the division has to be redone from the directory tree on every resize.
        # if i only use this in half-screen and full-screen sizes, it will never matter...
        for rect in self.rects:
            x = rect['x']
            y = rect['y']
            dx = rect['dx']
            dy = rect['dy']
            d = rect['depth']
            d = d % len(colormap)
            cs = colormap[d]

            self.canv.create_rectangle(x, y, x+dx, y+dy, width=1, fill=cs[0], outline='black')
            # self.canv.create_line(x, y+dy, x, y, x+dx, y, fill=cs[1])
            # self.canv.create_line(x, y+dy, x+dx, y+dy, x+dx, y, fill=cs[2])

            if rect['type'] == 'directory':
                text_x = x + text_offset_x
                text_y = y + text_offset_y
            elif rect['type'] == 'file':
                text_x = x + dx / 2
                text_y = y + dy / 2

            self.canv.create_text(text_x, text_y, text=rect['text'], fill="black",
                                  anchor=tk.NW, font=("Helvectica", text_size))


# TODO: maybe the compute_rectangles function should add rect positions to the tree struct directly
# then the mouse click hit test can retrieve the full struct directly

class TreemongerApp(object):
    # TODO: connect this
    action_map_keyboarde = {
        'q': 'quit',
        'r': 'refresh',
        'Up': 'zoomout',
        'Down': 'zoomin',
        't': 'top',
        'd': 'delete',
        'c': 'copy',
        'o': 'open',
        'f': 'find',
        'i': 'info'
    }
    # TODO connect this
    action_map_mouse = {
        1: ['info'],
        2: ['copy'],
        3: ['delete'],
        4: ['zoomout'],
        5: ['zoomin'],
    }
    def __init__(self, master, title, tree, compute_func, width=None, height=None):

        width = width or master.winfo_screenwidth()/2
        height = height or master.winfo_screenheight()/2

        self.master = master
        self.tree = tree
        self.render_root = '/'  # walk up and down tree to zoom
        self.compute_func = compute_func
        self.width = width
        self.height = height
        self.frame = tk.Frame(self.master)

        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()
        x = (screen_width / 2) - (width / 2)  # default window x position (centered)
        y = (screen_height / 2) - (height / 2)  # default window y position (centered)
        master.geometry('%dx%d+%d+%d' % (width, height, x, y))
        master.title(title)

        self.canv = tk.Canvas(master, bg='black')
        self.canv.pack(expand=True, fill=tk.BOTH)  # ?
        # canv.grid(row=0, column=0, columnspan=3);
        self.root_rect = self.canv.create_rectangle(0, 0, 0, 0, width=1,
                                                    fill="white", outline='black')
        self.canv.bind("<Configure>", self.on_resize)
        self.master.bind("<KeyPress>", self.on_keydown)
        self.master.bind("<KeyRelease>", self.on_keyup)
        self.canv.bind("<Button>", self.on_click)
        self.canv.bind_all("<MouseWheel>", self.on_mousewheel)
        self.frame.pack()

    def render(self, width=None, height=None):
        width = width or self.width
        height = height or self.height
        print('rendering %s %dx%d' % (self.render_root, width, height))

        # descend tree according to zoomstate variable render_root
        render_tree = self.tree
        if self.render_root != '/':
            parts = self.render_root.split('/')[1:]
            for p in parts:
                render_tree = render_tree[p]

        self.rects = self.compute_func(render_tree, [0, width], [0, height])
        for rect in self.rects:
            self.render_rect(rect)

    def render_label(self, rect):
        # TODO: variable font size here?
        x = rect['x']
        y = rect['y']
        dx = rect['dx']
        dy = rect['dy']
        d = rect['depth']
        d = d % len(colormap)
        cs = colormap[d]

    def render_rect(self, rect):
        x = rect['x']
        y = rect['y']
        dx = rect['dx']
        dy = rect['dy']
        d = rect['depth']
        d = d % len(colormap)
        cs = colormap[d]

        self.canv.create_rectangle(x, y, x+dx, y+dy, width=1, fill=cs[0], outline='black')
        self.canv.create_line(x+1, y+dy-1, x+1, y+1, x+dx-1, y+1, fill=cs[1])
        self.canv.create_line(x+1, y+dy-1, x+dx-1, y+dy-1, x+dx-1, y+1, fill=cs[2])

        if rect['type'] == 'directory':
            text_x = x + text_offset_x
            text_y = y + text_offset_y
            anchor = tk.NW
        elif rect['type'] == 'file':
            text_x = x + dx / 2
            text_y = y + dy / 2
            anchor = tk.CENTER

        clipped_text = shorten(rect['text'], dx, text_size)
        self.canv.create_text(text_x, text_y, text=clipped_text, fill="black",
                              anchor=anchor, font=("Helvectica", text_size))

    def find_rect(self, x, y):
        # TODO: it would be really nice if the rectangles and the tree nodes
        # were the same objects, so i could just traverse the tree right here...
        for rect in self.rects[::-1]:
            if rect['x'] <= x <= rect['x'] + rect['dx'] and rect['y'] <= y <= rect['y'] + rect['dy']:
                return rect

    def on_click(self, ev):
        print('click<%d>: (%d, %d), (%d, %d)' %
              (ev.num, ev.x, ev.y, ev.x_root, ev.y_root))
        rect = self.find_rect(ev.x, ev.y)

        # action_func = self.action_map_mouse.get(ev.num, [])

        if ev.num == 1:
            print('%s (%s)' %(rect['path'], rect['bytes']))
        if ev.num == 2:
            self.copypath(ev)
        if ev.num == 3:
            self.openfile(ev)
        if ev.num == 4:
            print('zoom out on: "%s"' % (rect['path']))
        if ev.num == 5:
            print('zoom in on: "%s"' % (rect['path']))
    
    def on_mousewheel(self, ev):
        print('mousewheel: %s' % ev)
        rect = self.find_rect(ev.x, ev.y)
        print('zooming on: "%s"' % (rect['path']))

    def on_resize(self, ev):
        print('resized: %d %d' % (ev.width, ev.height))
        self.width, self.height = ev.width, ev.height
        # self.canv.coords(self.root_rect, 1, 1, ev.width - 2, ev.height - 2)
        self.render()

    def on_keydown(self, ev):
        key = ev.keysym
        print('keydown: "%s"' % key)

    def on_keyup(self, ev):
        key = ev.keysym
        print('keyup: "%s"' % key)
        if key == 'q':
            self.quit()
        if key == 'r':
            self.refresh()
        if key == 'm':
            self.cycle_mode()
        if key == 'd':
            self.delete(ev)
        if key == 't':
            self.zoom_top()
        if key == 'c':
            print('copy')
            self.copypath(ev)
        if key == 'o':
            print('open')
            self.openfile(ev)
        if key == 'Up':
            self.zoom_out()
        if key == 'Down':
            self.zoom_in(ev)
        if key == 'Right':
            print('not yet implemented: navigate right in map')
        if key == 'Left':
            print('not yet implemented: navigate left in map')

    def quit(self):
        sys.exit(0)

    def refresh(self):
        print('not yet implemented: refresh')
        # TODO this requires passing a signal to scanner, and receiving the result
        # perhaps properly requires a refactor
        self.render()

    def zoom_top(self):
        self.render_root = '/'
        self.refresh()

    def zoom_out(self):
        parts = self.render_root.split('/')
        # TODO don't back up further than possible
        self.render_root = '/'.join(parts[:-1])
        self.refresh()

    def zoom_in(self, ev):
        p1 = self.render_root
        parts1 = p1.split('/')
        rect = self.find_rect(ev.x, ev.y)
        p2 = rect['path']
        parts2 = p2.split('/')
        if len(parts2) > len(parts1):
            parts2 = parts2[:len(parts1)+1]  # zoom in one level
        self.render_root = '/'.join(parts2)
        self.refresh()

    def cycle_mode(self):
        print('not yet implemented: mode cycle')
        # 0. total size
        # 1. total descendants

    def copypath(self, ev):
        rect = self.find_rect(ev.x, ev.y)
        if pyperclip_present:
            pyperclip.copy(rect['path'])
            print('copied to clipboard: "%s"' % (rect['path']))
        else:
            print('install pyperclip')

    def openfile(self, ev):
        rect = self.find_rect(ev.x, ev.y)
        print('opening: "%s"' % (rect['path']))
        open_file(rect['path'])

    def delete(self, ev):
        rect = self.find_rect(ev.x, ev.y)
        rect['path']
        # os.rm(rect['path'])
        # TODO: remove from tree struct too - hacky workaround to the bigger refactor - doesn't work with deleting externally
        print('deleted "%s"' % (rect['path']))
        


def render_class(tree, compute_func, title, width=None, height=None):
    """
    similar to render_class, but accepts the original tree rather than the computed rectangles
    this allows recalculation on resize etc
    """
    root = tk.Tk()
    app = TreemongerApp(root, title, tree, compute_func, width, height)
    app.render()
    root.mainloop()


def open_file(path):
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def render_class_old(rects, width, height, title):
    """
    same as render_function, but encapsulated into a class
    """
    root = tk.Tk()
    app = TreemongerAppOld(root, width, height, title)
    app.add_data(rects)
    app.render()
    root.mainloop()


def on_resize(ev):
    # canv.coords(line,0,0,ev.width,ev.height)
    print('resized: %d %d' % (ev.width, ev.height))

    # canv.coords(rect1, 1, 1, ev.width - 2, ev.height - 2)
    # render(t, canv, [3, ev.width - 4], [3, ev.height - 4])


def init(title, width, height):
    root = tk.Tk()

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width / 2) - (width / 2)  # default window x position (centered)
    y = (screen_height / 2) - (height / 2)  # default window y position (centered)
    root.geometry('%dx%d+%d+%d' % (width, height, x, y))

    root.title(title)

    # not sure if w and h do anything here
    # canv = tk.Canvas(root, width=w, height=h, bg='black')
    canv = tk.Canvas(root, bg='black')
    # canv = Canvas(root, bg = 'black')
    canv.pack(expand=True, fill=tk.BOTH)  # ?
    # canv.grid(row=0, column=0, columnspan=3);
    rect1 = canv.create_rectangle(
        0, 0, 0, 0, width=1, fill="white", outline='black')
    canv.bind("<Configure>", on_resize)
    # canv.bind("<Button-1>", on_click1)
    # canv.bind("<Button-2>", on_click2)
    # canv.bind("<Button-3>", on_click3)
    # canv.bind("<Button-4>", on_click4)
    # canv.bind("<Button-5>", on_click5)
    # root.bind("<KeyPress>", on_keydown)
    # root.bind("<KeyRelease>", on_keyup)

    return root, canv


def render_function(rects, width, height, title):
    # title = reverse_path(abspath(treepath))
    root, canv = init(title, width, height)
    print('%d rects' % len(rects))
    for rect in rects:
        x = rect['x']
        y = rect['y']
        dx = rect['dx']
        dy = rect['dy']
        d = rect['depth']
        d = d % len(colormap)
        cs = colormap[d]

        canv.create_rectangle(x, y, x+dx, y+dy, width=1, fill=cs[0], outline='black')
        canv.create_line(x, y+dy, x, y, x+dx, y, fill=cs[1])
        canv.create_line(x, y+dy, x+dx, y+dy, x+dx, y, fill=cs[2])

        if rect['type'] == 'directory':
            text_x = x + text_offset_x
            text_y = y + text_offset_y
        elif rect['type'] == 'file':
            text_x = x + dx / 2
            text_y = y + dy / 2

        canv.create_text(text_x, text_y, text=rect['text'], fill="black",
                         anchor=tk.NW, font=("Helvectica", text_size))

    root.mainloop()
