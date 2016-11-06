import Tkinter as tk

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


class TreemongerApp(object):
    def __init__(self, master, title, tree, compute_func, width=None, height=None):

        width = width or master.winfo_screenwidth()/2
        height = height or master.winfo_screenheight()/2

        self.master = master
        self.tree = tree
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
        self.canv.bind("<Button-1>", self.on_click1)
        self.canv.bind("<KeyPress>", self.on_keydown)
        self.canv.bind("<KeyRelease>", self.on_keyup)
        self.frame.pack()

    def render(self, *args, **kwargs):
        self.render_canvas(*args, **kwargs)

    def render_label(self, width=None, height=None):
        pass

    def render_canvas(self, width=None, height=None):
        width = width or self.width
        height = height or self.height
        print('rendering %dx%d' % (width, height))
        self.rects = self.compute_func(self.tree, [0, width], [0, height])
        for rect in self.rects:
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

    def on_click1(self, ev):
        print('left clicked: (%d, %d), (%d, %d)' %
              (ev.x, ev.y, ev.x_root, ev.y_root))

    def on_resize(self, ev):
        print('resized: %d %d' % (ev.width, ev.height))
        # self.canv.coords(self.root_rect, 1, 1, ev.width - 2, ev.height - 2)
        self.render(ev.width, ev.height)

    def on_keydown(self, ev):
        print('keydown: %s' % ev.char)

    def on_keyup(self, ev):
        print('keyup: %s' % ev.char)
        if ev.char == 'q':
            exit()
        if ev.char == 'r':
            print('not yet implemented: refresh')
            # requires combining everything into one big App class...
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


def render_class(tree, compute_func, title, width=None, height=None):
    """
    similar to render_class, but accepts the original tree rather than the computed rectangles
    this allows recalculation on resize etc
    """
    root = tk.Tk()
    app = TreemongerApp(root, title, tree, compute_func, width, height)
    app.render()
    root.mainloop()


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
