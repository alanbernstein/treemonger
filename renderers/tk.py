import datetime
import os
import shutil
import sys

from logger import logger

try:
    import pyperclip
    pyperclip_present = True
except:
    pyperclip_present = False

try:
    from send2trash import send2trash
    send2trash_present = True
except:
    send2trash_present = False

import tkinter as tk
from PIL import Image, ImageTk

from utils import shorten, open_file
from .colormap import colormap, trashed_color, trashed_text_color

# TODO: maybe the compute_rectangles function should add rect positions to the tree struct directly
# then the mouse click hit test can retrieve the full struct directly

class TreemongerApp(object):
    queue = []

    def __init__(self, master, title, scan_func, compute_func, config, width=None, height=None):
        self.config = config
        self.action_map_mouse = self._parse_keycombos(config['mouse'])
        self.action_map_keyboard = self._parse_keycombos(config['keyboard'])

        # Track trashed items for visual indication (path -> True)
        self.trashed_paths = set()
        # Store canvas item IDs for each rect path for fast partial updates
        # path -> {'rect_id': id, 'highlight_id': id, 'shadow_id': id, 'text_id': id}
        self.canvas_items = {}

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

        self._context_menu = None

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
            if k != '+' and '+' in k:
                k = k.split('+')
            # logger.info(f"{k}, {tuple(k)}, {v}"")
            if k in ['Up', 'Down', 'Right', 'Left']:
                res[(k,)] = v
            else:
                res[tuple(k)] = v
        return res

    def _print_usage(self):
        logger.info('UI usage:')
        for mouse_button, action_func_name in sorted(self.action_map_mouse.items()):
            logger.info('  mouse<%s>: %s' % (mouse_button, action_func_name))
        for key, action_func_name in sorted(self.action_map_keyboard.items()):
            if 'delete' in action_func_name:
                logger.info('  "%s": %s (WORK IN PROGRESS, USE AT YOUR OWN RISK!)' % (key, action_func_name))
            else:
                logger.info('  "%s": %s' % (key, action_func_name))

    def _cleanup_context_menu(self):
        if self._context_menu:
            self._context_menu.unpost()
            self._context_menu = None
            logger.trace('cleaning up context menu')
            return True
        return False

    def _render(self, width=None, height=None):
        width = width or self.width
        height = height or self.height
        logger.trace('rendering %s %dx%d' % (self.render_root, width, height))

        # Clear canvas item tracking (IDs will be recreated)
        self.canvas_items = {}

        # descend tree according to zoomstate variable render_root
        render_tree = self.tree
        render_root = self.render_root.lstrip(self.scan_root)
        if not render_root.startswith('/'):
            # annoying kludge to make _render and zoom_in work together, in both "cwd" and path argument cases
            render_root = '/' + render_root
        if render_root != '/':
            parts = render_root.split('/')[1:]
            for p in parts:
                logger.trace('getting %s' % p)
                render_tree = render_tree[p]

        zoom_depth = len(render_root.split('/')) - 1

        self.rects = self.compute_func(render_tree, [0, width], [0, height], self.config['tk_renderer'])
        for rect in self.rects:
            self._render_rect(rect, base_color_depth=zoom_depth)

    def render_label(self, rect):
        # TODO: variable font size here?
        logger.trace('render_label')
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

        # Use trashed colors if this path has been trashed
        is_trashed = rect['path'] in self.trashed_paths
        if is_trashed:
            cs = trashed_color
            text_fill = trashed_text_color
        else:
            cs = colormap[d]
            text_fill = "black"

        rect_id = self.canv.create_rectangle(x, y, x+dx, y+dy, width=1, fill=cs[0], outline='black')
        highlight_id = self.canv.create_line(x+1, y+dy-1, x+1, y+1, x+dx-1, y+1, fill=cs[1])
        shadow_id = self.canv.create_line(x+1, y+dy-1, x+dx-1, y+dy-1, x+dx-1, y+1, fill=cs[2])

        if rect['type'] == 'directory':
            text_x = x + self.config['tk_renderer']['text_offset_x']
            text_y = y + self.config['tk_renderer']['text_offset_y']
            anchor = tk.NW
        elif rect['type'] == 'file':
            text_x = x + dx / 2
            text_y = y + dy / 2
            anchor = tk.CENTER

        clipped_text = shorten(rect['text'], dx, self.config['tk_renderer']['text_size'])
        text_id = self.canv.create_text(text_x, text_y, text=clipped_text, fill=text_fill,
                              anchor=anchor, font=("Helvectica", self.config['tk_renderer']['text_size']))

        # Store canvas item IDs for fast partial updates
        self.canvas_items[rect['path']] = {
            'rect_id': rect_id,
            'highlight_id': highlight_id,
            'shadow_id': shadow_id,
            'text_id': text_id,
        }

    def _find_rect(self, x, y):
        # TODO: it would be really nice if the rectangles and the tree nodes
        # were the same objects, so i could just traverse the tree right here...
        for rect in self.rects[::-1]:
            if rect['x'] <= x <= rect['x'] + rect['dx'] and rect['y'] <= y <= rect['y'] + rect['dy']:
                return rect

    def _on_mousewheel(self, ev):
        if self._cleanup_context_menu():
            return
        logger.trace('mousewheel: %s' % ev)
        rect = self._find_rect(ev.x, ev.y)
        logger.trace('zooming on: "%s"' % (rect['path']))

    def _on_resize(self, ev):
        if self._cleanup_context_menu():
            return
        logger.trace('resized: %d %d' % (ev.width, ev.height))
        self.width, self.height = ev.width, ev.height
        # self.canv.coords(self.root_rect, 1, 1, ev.width - 2, ev.height - 2)
        self._render()

    def _on_click(self, ev):
        if self._cleanup_context_menu():
            return
        mouse_button = ev.num
        s = ev.state
        modifiers = []
        if (s & 0x1):
            modifiers.append('shift')
        if (s & 0x4):
            modifiers.append('ctrl')
        if (s & 0x88):
            modifiers.append('alt')

        logger.trace(f"{modifiers} {mouse_button}")
        combo = tuple(modifiers + [str(mouse_button)])
        logger.trace(combo)
        logger.trace('mouse<%d> %s' % (mouse_button, combo))
        action_func_name = self.action_map_mouse.get(combo, '')
        if action_func_name == '':
            logger.trace('  event mouse<%s>: no action defined' % (combo, ))
            return
        action_func = getattr(self, action_func_name)
        action_func(ev)

    def _on_keydown(self, ev):
        if self._cleanup_context_menu():
            return
        key = ev.keysym
        logger.trace('keydown: "%s"' % key)

    def _on_keyup(self, ev):
        if self._cleanup_context_menu():
            return
        key = ev.keysym
        s = ev.state
        modifiers = []
        if (s & 0x1):
            modifiers.append('shift')
        if (s & 0x4):
            modifiers.append('ctrl')
        if (s & 0x88):
            modifiers.append('alt')
        logger.trace(f"{modifiers} {key}")
        key_ = key
        if key_ not in ['Up', 'Down', 'Left', 'Right']:
            key_ = key_.lower()

        combo = tuple(modifiers + [key_])
        logger.trace(combo)
        logger.trace('keyup: "%s" (%s)' % (key, combo))
        action_func_name = self.action_map_keyboard.get(combo, '')
        if action_func_name == '':
            logger.trace('  event "%s": no action defined' % (combo, ))
            return
        action_func = getattr(self, action_func_name)
        action_func(ev)

    def context_menu(self, ev):
        rect = self._find_rect(ev.x, ev.y)
        # TODO: generalize
        # TODO: may want to init menu once and reconfigure per event
        m = tk.Menu(self.master, tearoff = 0)
        m.add_command(label=rect['path'], foreground='grey', command=lambda: None)
        m.add_separator()
        m.add_command(label="info", underline=0, command=lambda: self.info(ev))
        m.add_command(label="copy path", underline=0, command=lambda: self.copy_path(ev))
        m.add_command(label="open location", underline=0, command=lambda: self.open_location(ev))
        m.add_command(label="refresh", underline=0, command=lambda: self.refresh(ev))
        m.add_separator()
        m.add_command(label="move to trash", underline=8, command=lambda: self.trash_path(ev))
        m.add_separator()
        m.add_command(label="add to delete queue", underline=0, command=lambda: self.add_to_queue(ev, "delete"))
        m.add_command(label="print queue", underline=0, command=lambda: self.print_queue(ev))
        m.add_command(label="execute queue", underline=1, command=lambda: self.execute_queue(ev))
        #m.add_command(label="delete", underline=0, command=lambda: self.delete_file(ev))
        self._context_menu = m

        def on_menu_close():
            self._context_menu = None

        m.bind('<Unmap>', lambda e: on_menu_close())
        m.bind('<FocusOut>', lambda e: self._cleanup_context_menu())
        m.tk_popup(ev.x_root, ev.y_root)

    def quit(self, ev):
        sys.exit(0)

    def info(self, ev):
        logger.info('  (%d, %d), (%d, %d)' %
              (ev.x, ev.y, ev.x_root, ev.y_root))
        rect = self._find_rect(ev.x, ev.y)
        logger.trace('  %s (%s)' % (rect['path'], rect['bytes']))

    def refresh(self, ev):
        self.tree = self.scan_func()
        logger.trace('  refresh')
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
        self._render()

    def cycle_mode(self, ev):
        logger.info('  cycle_mode: not yet implemented')
        # 0. total size
        # 1. total descendants

    def copy_path(self, ev):
        # https://unix.stackexchange.com/questions/139191/whats-the-difference-between-primary-selection-and-clipboard-buffer
        rect = self._find_rect(ev.x, ev.y)
        if pyperclip_present:
            pyperclip.copy(rect['path'])
            logger.info('  copied to clipboard: "%s"' % (rect['path']))
        else:
            logger.error('  copy_path: dependency `pyperclip` not available')
            logger.error('  install with: pip install pyperclip')

    def open_file(self, ev):
        rect = self._find_rect(ev.x, ev.y)
        logger.info('  open file: "%s"' % (rect['path']))
        open_file(rect['path'])

    def open_location(self, ev):
        rect = self._find_rect(ev.x, ev.y)
        if rect['type'] == 'directory':
            location = rect['path']
        else:
            location = os.path.dirname(rect['path'])
        logger.info('  open location: "%s"' % location)
        open_file(location)

    def add_to_queue(self, ev, action):
        rect = self._find_rect(ev.x, ev.y)
        self.queue.append({
            "action": action,
            "path": rect["path"],
        })

    def print_queue(self, ev):
        logger.info('action queue:')
        for a in self.queue:
            logger.info(f"  {a['action']}: {a['path']}")

    def execute_queue(self, ev):
        for a in self.queue:
            if a["action"] == "delete":
                logger.info(f"rm \"{a['path']}\"")
                #os.remove(a["path"])

    def clear_queue(self, ev):
        self.queue = []

    def delete_tree(self, ev):
        rect = self._find_rect(ev.x, ev.y)
        SAFE_MODE = True
        if SAFE_MODE:
            logger.info('  delete_tree: not available with SAFE_MODE = True')
            return

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

        logger.info('  delete_tree: %s' % rect['path'])

    def _mark_rect_as_trashed(self, path):
        """Fast partial update: visually mark a single rect as trashed without full re-render."""
        if path not in self.canvas_items:
            logger.warning(f'  _mark_rect_as_trashed: no canvas items for path "{path}"')
            return False

        items = self.canvas_items[path]
        self.canv.itemconfig(items['rect_id'], fill=trashed_color[0])
        self.canv.itemconfig(items['highlight_id'], fill=trashed_color[1])
        self.canv.itemconfig(items['shadow_id'], fill=trashed_color[2])
        self.canv.itemconfig(items['text_id'], fill=trashed_text_color)
        return True

    def trash_path(self, ev):
        """Move file/folder to system trash and visually mark as trashed."""
        rect = self._find_rect(ev.x, ev.y)
        path = rect['path']

        if not send2trash_present:
            logger.error('  trash_path: dependency `send2trash` not available')
            logger.error('  install with: pip install send2trash')
            return

        if path in self.trashed_paths:
            logger.info(f'  trash_path: "{path}" already trashed')
            return

        try:
            logger.info(f'  trash_path: moving to trash: "{path}"')
            send2trash(path)
            logger.trace(f'  trash_path: sent')

            # Use absolute path for logging
            abs_path = os.path.abspath(path) if path.startswith("./") else path

            # Mark as trashed and update visuals (use original path to match rects)
            self.trashed_paths.add(path)
            logger.trace(f'  trash_path: marked')

            # Also mark all children as trashed (if it was a directory)
            for r in self.rects:
                if r['path'].startswith(path + '/') or r['path'] == path:
                    self.trashed_paths.add(r['path'])
                    self._mark_rect_as_trashed(r['path'])
            logger.trace(f'  trash_path: marked children')

            # Log to file
            trash_log = self.config["trash-log-file"]
            if trash_log:
                with open(trash_log, 'a') as f:
                    timestamp = datetime.datetime.now().isoformat()
                    f.write(f'{timestamp} {abs_path}\n')
                logger.trace(f'  trash_path: logged to {trash_log}')
            else:
                logger.warning(f'not logging trashed file path. set flags:trash-log-pattern in config file to log.')

        except Exception as e:
            logger.error(f'  trash_path: error moving to trash: {e}')

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
    current_dir = os.path.dirname(os.path.abspath(__file__))
    icon_fname = current_dir + "/../treemonger-icon.png"
    icon_image = Image.open(icon_fname)
    icon = ImageTk.PhotoImage(icon_image)
    root.iconphoto(False, ImageTk.PhotoImage(file=icon_fname))
    app = TreemongerApp(root, title, scan_func, subdivide_func, config, width, height)
    app._render()
    root.mainloop()
