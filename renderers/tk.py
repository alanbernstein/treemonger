import Tkinter as tk

from .colormap import colormap
from constants import (text_size,
                       text_offset_x,
                       text_offset_y,
                       )


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


def render(rects, width, height, title):
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
