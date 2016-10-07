import Tkinter as tk

from .colormap import colormap


def init(title):
    root = tk.Tk()

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    w = screen_width / 2            # default window width
    h = screen_height / 2           # default window height
    x = (screen_width / 2) - (w / 2)  # default window x position (centered)
    y = (screen_height / 2) - (h / 2)  # default window y position (centered)
    root.geometry('%dx%d+%d+%d' % (w, h, x, y))

    root.title(title)

    # not sure if w and h do anything here
    canv = tk.Canvas(root, width=w, height=h, bg='black')
    # canv = Canvas(root, bg = 'black')
    canv.pack(expand=True, fill=tk.BOTH)  # ?
    # canv.grid(row=0, column=0, columnspan=3);
    rect1 = canv.create_rectangle(
        0, 0, 0, 0, width=1, fill="white", outline='black')
    # canv.bind("<Configure>", on_resize)
    # canv.bind("<Button-1>", on_click1)
    # canv.bind("<Button-2>", on_click2)
    # canv.bind("<Button-3>", on_click3)
    # canv.bind("<Button-4>", on_click4)
    # canv.bind("<Button-5>", on_click5)
    # root.bind("<KeyPress>", on_keydown)
    # root.bind("<KeyRelease>", on_keyup)

    return root, canv


def render(rects):
    # title = reverse_path(abspath(treepath))
    title = 'title placeholder'
    root, canv = init(title)
    print('%d rects' % len(rects))
    for rect in rects:
        x = rect['x']
        y = rect['y']
        dx = rect['dx']
        dy = rect['dy']
        cs = colormap[rect['depth']]

        canv.create_rectangle(x, y, x+dx, y+dy, width=1, fill=cs[0], outline='black')
        canv.create_line(x, y+dy, x, y, x+dx, y, fill=cs[1])
        canv.create_line(x, y+dy, x+dx, y+dy, x+dx, y, fill=cs[2])

        if rect['type'] == 'directory':
            pass
        elif rect['type'] == 'file':
            pass

    root.mainloop()
