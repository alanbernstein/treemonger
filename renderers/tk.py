import os
import shutil
import sys

try:
    import pyperclip
    pyperclip_present = True
except:
    pyperclip_present = False

import tkinter as tk

from utils import shorten, open_file
from .colormap import colormap

# TODO: maybe the compute_rectangles function should add rect positions to the tree struct directly
# then the mouse click hit test can retrieve the full struct directly

class TreemongerApp(object):
    def __init__(self, master, title, scan_func, compute_func, config, width=None, height=None):
        self.config = config
        self.action_map_mouse = self._parse_keycombos(config['mouse'])
        self.action_map_keyboard = self._parse_keycombos(config['keyboard'])
        print(self.config)

        self.scan_func = scan_func
        self.tree = self.scan_func()
        self.scan_root = self.tree.path

        self.compute_func = compute_func
        self.render_root = '/'  # walk up and down tree to zoom

        self.master = master
        self.frame = tk.Frame(self.master)
        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()
        width = width or screen_width/2
        height = height or screen_height/2
        self.width = width
        self.height = height

        x = (screen_width / 2) - (width / 2)  # default window x position (centered)
        y = (screen_height / 2) - (height / 2)  # default window y position (centered)
        master.geometry('%dx%d+%d+%d' % (width, height, x, y))
        master.title(title)

        self.canv = tk.Canvas(master, bg='black')
        self.canv.pack(expand=True, fill=tk.BOTH)  # ?
        # canv.grid(row=0, column=0, columnspan=3);
        self.root_rect = self.canv.create_rectangle(0, 0, 0, 0, width=1,
                                                    fill="white", outline='black')
        self.master.bind("<KeyPress>", self._on_keydown)
        self.master.bind("<KeyRelease>", self._on_keyup)
        self.canv.bind("<Configure>", self._on_resize)
        self.canv.bind("<Button>", self._on_click)
        self.canv.bind_all("<MouseWheel>", self._on_mousewheel)
        self.frame.pack()

        self._print_usage()

    def _parse_keycombos(self, cnf):
        res = {}
        for k, v in cnf.items():
            if '+' in k:
                k = k.split('+')
            print(k, tuple(k), v)
            res[tuple(k)] = v
        return res

    def _print_usage(self):
        print('UI usage:')
        for mouse_button, action_func_name in sorted(self.action_map_mouse.items()):
            print('  mouse<%s>: %s' % (mouse_button, action_func_name))
        for key, action_func_name in sorted(self.action_map_keyboard.items()):
            if 'delete' in action_func_name:
                print('  "%s": %s (WORK IN PROGRESS, USE AT YOUR OWN RISK!)' % (key, action_func_name))
            else:
                print('  "%s": %s' % (key, action_func_name))

    def _render(self, width=None, height=None):
        width = width or self.width
        height = height or self.height
        print('rendering %s %dx%d' % (self.render_root, width, height))

        # descend tree according to zoomstate variable render_root
        render_tree = self.tree
        render_root = self.render_root.lstrip(self.scan_root)
        if not render_root.startswith('/'):
            # annoying kludge to make _render and zoom_in work together, in both "cwd" and path argument cases
            render_root = '/' + render_root
        if render_root != '/':
            parts = render_root.split('/')[1:]
            for p in parts:
                print('getting %s' % p)
                render_tree = render_tree[p]

        zoom_depth = len(render_root.split('/')) - 1

        self.rects = self.compute_func(render_tree, [0, width], [0, height], self.config['tk_renderer'])
        for rect in self.rects:
            self._render_rect(rect, base_color_depth=zoom_depth)

    def render_label(self, rect):
        # TODO: variable font size here?
        print('render_label')
        x = rect['x']
        y = rect['y']
        dx = rect['dx']
        dy = rect['dy']
        d = rect['depth']
        d = d % len(colormap)
        cs = colormap[d]

    def _render_rect(self, rect, base_color_depth=0):
        x = rect['x']
        y = rect['y']
        dx = rect['dx']
        dy = rect['dy']
        d = rect['depth']
        d = (d + base_color_depth) % len(colormap)
        cs = colormap[d]

        self.canv.create_rectangle(x, y, x+dx, y+dy, width=1, fill=cs[0], outline='black')
        self.canv.create_line(x+1, y+dy-1, x+1, y+1, x+dx-1, y+1, fill=cs[1])
        self.canv.create_line(x+1, y+dy-1, x+dx-1, y+dy-1, x+dx-1, y+1, fill=cs[2])

        if rect['type'] == 'directory':
            text_x = x + self.config['tk_renderer']['text_offset_x']
            text_y = y + self.config['tk_renderer']['text_offset_y']
            anchor = tk.NW
        elif rect['type'] == 'file':
            text_x = x + dx / 2
            text_y = y + dy / 2
            anchor = tk.CENTER

        clipped_text = shorten(rect['text'], dx, self.config['tk_renderer']['text_size'])
        self.canv.create_text(text_x, text_y, text=clipped_text, fill="black",
                              anchor=anchor, font=("Helvectica", self.config['tk_renderer']['text_size']))

    def _find_rect(self, x, y):
        # TODO: it would be really nice if the rectangles and the tree nodes
        # were the same objects, so i could just traverse the tree right here...
        for rect in self.rects[::-1]:
            if rect['x'] <= x <= rect['x'] + rect['dx'] and rect['y'] <= y <= rect['y'] + rect['dy']:
                return rect

    def _on_mousewheel(self, ev):
        print('mousewheel: %s' % ev)
        rect = self._find_rect(ev.x, ev.y)
        print('zooming on: "%s"' % (rect['path']))

    def _on_resize(self, ev):
        print('resized: %d %d' % (ev.width, ev.height))
        self.width, self.height = ev.width, ev.height
        # self.canv.coords(self.root_rect, 1, 1, ev.width - 2, ev.height - 2)
        self._render()

    def _on_click(self, ev):
        mouse_button = ev.num
        s = ev.state
        modifiers = []
        if (s & 0x1):
            modifiers.append('shift')
        if (s & 0x4):
            modifiers.append('ctrl')
        if (s & 0x88):
            modifiers.append('alt')

        print(modifiers, mouse_button)
        combo = tuple(modifiers + [str(mouse_button)])
        print(combo)
        print('mouse<%d> %s' % (mouse_button, combo))
        self.info(ev)
        action_func_name = self.action_map_mouse.get(combo, '')
        if action_func_name == '':
            print('  event mouse<%s>: no action defined' % (combo, ))
            return
        action_func = getattr(self, action_func_name)
        action_func(ev)

    def _on_keydown(self, ev):
        key = ev.keysym
        print('keydown: "%s"' % key)

    def _on_keyup(self, ev):
        key = ev.keysym
        s = ev.state
        modifiers = []
        if (s & 0x1):
            modifiers.append('shift')
        if (s & 0x4):
            modifiers.append('ctrl')
        if (s & 0x88):
            modifiers.append('alt')
        print(modifiers, key)
        combo = tuple(modifiers + [key.lower()])
        print(combo)
        print('keyup: "%s" (%s)' % (key, combo))
        action_func_name = self.action_map_keyboard.get(combo, '')
        if action_func_name == '':
            print('  event "%s": no action defined' % (combo, ))
            return
        action_func = getattr(self, action_func_name)
        action_func(ev)

    def context_menu(self, ev):
        m = tk.Menu(self.master, tearoff = 0)
        m.add_command(label ="Info (i)", command=lambda: self.info(ev))
        m.add_command(label ="Copy path (c)", command=lambda: self.copy_path(ev))
        m.add_command(label ="Open location (o)", command=lambda: self.open_location(ev))
        m.add_command(label ="Refresh (r)", command=lambda: self.refresh(ev))
        m.add_separator()
        m.add_command(label ="Delete (d)", command=lambda: self.delete_file(ev))
        try:
            m.tk_popup(ev.x_root, ev.y_root)
        finally:
            m.grab_release()

    def quit(self, ev):
        sys.exit(0)

    def info(self, ev):
        print('  (%d, %d), (%d, %d)' %
              (ev.x, ev.y, ev.x_root, ev.y_root))
        rect = self._find_rect(ev.x, ev.y)
        print('  %s (%s)' % (rect['path'], rect['bytes']))

    def refresh(self, ev):
        self.tree = self.scan_func()
        print('  refresh')
        self._render()

    def zoom_top(self, ev):
        self.render_root = '/'
        self.refresh(ev)

    def zoom_out(self, ev):
        parts = self.render_root.split('/')
        # TODO don't back up further than possible
        self.render_root = '/'.join(parts[:-1])
        self.refresh(ev)

    def zoom_in(self, ev):
        # append one directory level to zoom state
        p1 = self.render_root
        parts1 = p1.split('/')
        rect = self._find_rect(ev.x, ev.y)
        p2 = rect['path'].lstrip(self.scan_root)
        parts2 = p2.split('/')
        if len(parts2) > len(parts1):
            parts2 = parts2[:len(parts1)+1]  # zoom in one level
        self.render_root = '/'.join(parts2)

        # then render
        self._render(ev)

    def cycle_mode(self, ev):
        print('  cycle_mode: not yet implemented')
        # 0. total size
        # 1. total descendants

    def copy_path(self, ev):
        # https://unix.stackexchange.com/questions/139191/whats-the-difference-between-primary-selection-and-clipboard-buffer
        rect = self._find_rect(ev.x, ev.y)
        if pyperclip_present:
            pyperclip.copy(rect['path'])
            print('  copied to clipboard: "%s"' % (rect['path']))
        else:
            print('  copy_path: dependency `pyperclip` not available')

    def open_file(self, ev):
        rect = self._find_rect(ev.x, ev.y)
        print('  open file: "%s"' % (rect['path']))
        open_file(rect['path'])

    def open_location(self, ev):
        rect = self._find_rect(ev.x, ev.y)
        location = os.path.dirname(rect['path'])
        print('  open location: "%s"' % location)
        open_file(location)

    def delete_file(self, ev):
        rect = self._find_rect(ev.x, ev.y)
        if rect['type'] == 'directory':
            shutil.rmtree(rect['path'])
        else:
            os.remove(rect['path'])
        
        # TODO: don't rescan the whole tree, instead remove node directly
        # NOTE: this has to be SUPER robust, because one potential failure
        # mode is that the real file gets deleted, the app updates the render,
        # but does NOT update the canvas. then, the next delete event can delete
        # an unexpected file - BAD

        #path = '/'.join(rect['path'].split('/')[1:])
        #self.tree.delete_child(path)
        #self._render()
        
        self.refresh(ev)
        
        print('  delete: %s' % rect['path'])

def init_app(scan_func, subdivide_func, config, title, width=None, height=None):
    """
    similar to render_class, but accepts the original tree rather than the computed rectangles
    this allows recalculation on resize etc
    """
    # TODO: invert the structure so the TK app has a member function to 
    # compute the rects. 'render_class" design assumes we'll define
    # other types of renderer, but the only other idea i have for that is
    # svg, which produces a static output file. just simplify for the TK case.
    
    # svg might be interactive, but
    # it won't use a 'refresh' action in the same way. that would probably 
    # be best done with a self-hosted web app... lightweight JS wrapper to
    # provide hot-reload capability, with a python backend that uses modules 
    # from here for scanner, filesystem actions, maybe 2D subdivision (or use
    # an off-the-shelf vis library for that? not sure if anything exists that
    # would produce the interactivity i'd like to see in an svg)

    root = tk.Tk()
    app = TreemongerApp(root, title, scan_func, subdivide_func, config, width, height)
    app._render()
    root.mainloop()
