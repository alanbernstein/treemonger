import datetime
import logging
import mimetypes
import os
import shutil
import sys
import time

from logger import logger


class TkTextHandler(logging.Handler):
    """Logging handler that writes to a Tk Text widget."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        # Schedule on main thread (Tk isn't thread-safe)
        self.text_widget.after(0, self._append, msg)

    def _append(self, msg):
        self.text_widget.insert('end', msg + '\n')
        self.text_widget.see('end')

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

from utils import shorten, open_file, format_combo, get_mousebutton_names, format_bytes
from .colormap import colormap, special_colors

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
        # Track highlighted items from filter
        self.highlighted_paths = set()
        self._base_color_depth = 0
        self._filter_log_job = None
        # Store canvas item IDs for each rect path for fast partial updates
        # path -> {'rect_id': id, 'highlight_id': id, 'shadow_id': id, 'text_id': id}
        self.canvas_items = {}
        # Track last hovered rect for keyboard actions when mouse isn't over canvas
        self._last_hovered_rect = None

        # Load special colors from config with fallback to colormap defaults
        tk_conf = config.get('tk_renderer', {})
        self._trashed_color = tk_conf.get('trashed_color', special_colors['trashed']['color'])
        self._trashed_text_color = tk_conf.get('trashed_text_color', special_colors['trashed']['text_color'])
        self._highlight_color = tk_conf.get('highlight_color', special_colors['highlight']['color'])
        self._highlight_text_color = tk_conf.get('highlight_text_color', special_colors['highlight']['text_color'])

        self.scan_func = scan_func
        self.tree = self.scan_func()
        self.scan_root = self.tree.path

        self.compute_func = compute_func
        self.render_root = '/'  # walk up and down tree to zoom

        self.master = master
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
        self._help_window = None
        self._resize_job = None
        self._last_zoom_time = 0
        self._zoom_cooldown = 0.5  # seconds

        # Check config for console
        show_console = self.config.get('tk_renderer', {}).get('show_console', False)

        # Grid layout: row 0 = content, row 1 = status bar
        master.grid_rowconfigure(0, weight=1)
        master.grid_columnconfigure(0, weight=1)

        # Main content frame (holds canvas and optionally console)
        content_frame = tk.Frame(master)
        content_frame.grid(row=0, column=0, sticky='nsew')
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)

        # Canvas
        self.canv = tk.Canvas(content_frame, bg='black')
        self.canv.grid(row=0, column=0, sticky='nsew')
        self.root_rect = self.canv.create_rectangle(0, 0, 0, 0, width=1,
                                                    fill="white", outline='black')

        # Console (if enabled)
        if show_console:
            self._setup_console(content_frame)

        # Status bar
        self._setup_status_bar()

        # Event bindings
        self.master.bind("<KeyPress>", self._on_keydown)
        self.master.bind("<KeyRelease>", self._on_keyup)
        self.canv.bind("<Configure>", self._on_resize)
        self.canv.bind("<Button>", self._on_canvas_click)
        self.canv.bind("<Motion>", self._on_hover)
        self.canv.bind_all("<MouseWheel>", self._on_mousewheel)

        # Ensure canvas has focus so keyboard shortcuts work (not the filter entry)
        self.canv.focus_set()

        # self._print_usage()
        self._print_help_shortcut()

    def _setup_status_bar(self):
        """Status bar: info on left, filter on right."""
        self.status_bar = tk.Frame(self.master)
        self.status_bar.grid(row=1, column=0, sticky='ew')

        # Info label on left
        self.status_label = tk.Label(self.status_bar, text="Ready", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, padx=5)

        # Filter on right
        filter_frame = tk.Frame(self.status_bar)
        filter_frame.pack(side=tk.RIGHT, padx=5)
        tk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT)
        self.filter_entry = tk.Entry(filter_frame, width=15)
        self.filter_entry.pack(side=tk.LEFT, padx=2)
        self.filter_entry.bind('<KeyRelease>', self._on_filter_change)
        self.filter_entry.bind('<Tab>', self._on_filter_tab)
        self.filter_entry.bind('<Return>', lambda e: self._on_filter_change(e))
        self.filter_entry.bind('<Escape>', self._on_filter_escape)

    def _setup_console(self, parent):
        """Console panel on the right side."""
        console_width = 350
        console_bg = '#1e1e1e'
        console_fg = '#cccccc'

        self.console_frame = tk.Frame(parent, bg=console_bg, width=console_width)
        self.console_frame.grid(row=0, column=1, sticky='ns')
        self.console_frame.grid_propagate(False)

        tk.Label(self.console_frame, text="Console", bg=console_bg, fg=console_fg,
                 font=('Helvetica', 9, 'bold')).pack(anchor='w', padx=5, pady=(5, 0))

        self.console_text = tk.Text(self.console_frame, wrap=tk.WORD,
                                    bg=console_bg, fg=console_fg, width=40)
        console_scroll = tk.Scrollbar(self.console_frame, command=self.console_text.yview)
        self.console_text.config(yscrollcommand=console_scroll.set)
        console_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.console_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Add logging handler to mirror output to console
        self._console_handler = TkTextHandler(self.console_text)
        self._console_handler.setFormatter(logging.Formatter('%(levelname)-8s | %(message)s'))
        logger.addHandler(self._console_handler)

    def _on_filter_change(self, event=None):
        """Handle filter text changes — auto-apply highlighting."""
        filter_text = self.filter_entry.get().strip()
        if not filter_text:
            self._clear_highlight()
            return

        matching_paths = set()
        for rect in self.rects:
            path = rect['path']
            is_dir = rect['type'] == 'directory'
            if filter_text.startswith('.'):
                # Extension filter (files only)
                if not is_dir and path.endswith(filter_text):
                    matching_paths.add(path)
            elif filter_text.startswith(':'):
                # MIME category filter (files only)
                if not is_dir:
                    category = filter_text[1:].lower()
                    mime_type, _ = mimetypes.guess_type(path)
                    if mime_type and mime_type.split('/')[0] == category:
                        matching_paths.add(path)
            elif filter_text.endswith('/'):
                # Trailing slash: match directories only
                if is_dir:
                    query = filter_text[:-1].lower()
                    dirname = os.path.basename(path)
                    if query in dirname.lower():
                        matching_paths.add(path)
            else:
                # Substring match on name (files and directories)
                name = os.path.basename(path)
                if filter_text.lower() in name.lower():
                    matching_paths.add(path)

        self._apply_highlight(matching_paths)

    def _apply_highlight(self, matching_paths):
        """Apply highlight to matching paths, restore others."""
        to_highlight = matching_paths - self.highlighted_paths
        to_restore = self.highlighted_paths - matching_paths

        for path in to_highlight:
            if path not in self.trashed_paths:
                self._mark_rect_as_highlighted(path)

        for path in to_restore:
            if path not in self.trashed_paths:
                self._restore_rect_color(path)

        self.highlighted_paths = matching_paths
        filter_text = self.filter_entry.get().strip()

        # Walk full tree for stats (not just visible rects)
        total_count, total_bytes = self._count_tree_matches(filter_text)
        visible_count = len(matching_paths)
        self.set_status(f"Filter: {filter_text} ({total_count} file{'s' if total_count != 1 else ''}, {format_bytes(total_bytes)})")
        # Debounce log message so it only fires when the user pauses typing
        if self._filter_log_job:
            self.master.after_cancel(self._filter_log_job)
        self._filter_log_job = self.master.after(400, lambda: logger.info(
            f"Filter: {filter_text} — {total_count} file{'s' if total_count != 1 else ''}, {format_bytes(total_bytes)} ({visible_count} visible)"))

    def _count_tree_matches(self, filter_text):
        """Walk the full tree and count files/bytes matching the filter."""
        count = 0
        total = 0
        stack = [self.tree]
        while stack:
            node = stack.pop()
            is_dir = bool(node.children)
            name = os.path.basename(node.path)
            matched = False
            if filter_text.startswith('.'):
                if not is_dir and node.path.endswith(filter_text):
                    matched = True
            elif filter_text.startswith(':'):
                if not is_dir:
                    category = filter_text[1:].lower()
                    mime_type, _ = mimetypes.guess_type(node.path)
                    if mime_type and mime_type.split('/')[0] == category:
                        matched = True
            elif filter_text.endswith('/'):
                if is_dir:
                    query = filter_text[:-1].lower()
                    if query in name.lower():
                        matched = True
            else:
                if filter_text.lower() in name.lower():
                    matched = True
            if matched:
                count += 1
                total += node.size
            stack.extend(node.children)
        return count, total

    def _mark_rect_as_highlighted(self, path):
        """Fast partial update: visually mark a single rect as highlighted."""
        if path not in self.canvas_items:
            return
        items = self.canvas_items[path]
        self.canv.itemconfig(items['rect_id'], fill=self._highlight_color[0])
        self.canv.itemconfig(items['highlight_id'], fill=self._highlight_color[1])
        self.canv.itemconfig(items['shadow_id'], fill=self._highlight_color[2])
        self.canv.itemconfig(items['text_id'], fill=self._highlight_text_color)

    def _restore_rect_color(self, path):
        """Restore a rect to its original depth-based color."""
        if path in self.trashed_paths:
            return
        if path not in self.canvas_items:
            return
        # Find the rect to get its depth
        for rect in self.rects:
            if rect['path'] == path:
                d = (rect['depth'] + self._base_color_depth) % len(colormap)
                cs = colormap[d]
                items = self.canvas_items[path]
                self.canv.itemconfig(items['rect_id'], fill=cs[0])
                self.canv.itemconfig(items['highlight_id'], fill=cs[1])
                self.canv.itemconfig(items['shadow_id'], fill=cs[2])
                self.canv.itemconfig(items['text_id'], fill="black")
                return

    def _clear_highlight(self):
        """Remove all filter highlighting and restore original colors."""
        if self.highlighted_paths:
            logger.info("Filter cleared")
        for path in self.highlighted_paths:
            self._restore_rect_color(path)
        self.highlighted_paths = set()
        self.set_status("Ready")

    def _on_filter_tab(self, event):
        """Tab-completion for filter entry."""
        text = self.filter_entry.get().strip()
        if not text:
            return "break"

        completions = []
        if text.startswith('.'):
            # Collect unique extensions
            extensions = set()
            for rect in self.rects:
                if rect['type'] == 'file':
                    _, ext = os.path.splitext(rect['path'])
                    if ext:
                        extensions.add(ext)
            completions = sorted(e for e in extensions if e.startswith(text))
        elif text.startswith(':'):
            # Collect MIME categories present in current view
            categories = set()
            for rect in self.rects:
                if rect['type'] == 'file':
                    mime_type, _ = mimetypes.guess_type(rect['path'])
                    if mime_type:
                        categories.add(':' + mime_type.split('/')[0])
            completions = sorted(c for c in categories if c.startswith(text))

        if len(completions) == 1:
            self.filter_entry.delete(0, tk.END)
            self.filter_entry.insert(0, completions[0])
            self._on_filter_change()
        elif len(completions) > 1:
            # Fill to longest common prefix
            prefix = os.path.commonprefix(completions)
            if len(prefix) > len(text):
                self.filter_entry.delete(0, tk.END)
                self.filter_entry.insert(0, prefix)
            logger.info(f"Completions: {', '.join(completions)}")

        return "break"

    def _on_filter_escape(self, event):
        """Clear filter and unfocus."""
        self.filter_entry.delete(0, tk.END)
        self._clear_highlight()
        self.canv.focus_set()
        return "break"

    def set_status(self, text):
        """Update status bar text."""
        self.status_label.config(text=text)

    def log_to_console(self, text):
        """Add text to console (if enabled)."""
        if not hasattr(self, 'console_text'):
            return
        self.console_text.insert(tk.END, text + "\n")
        self.console_text.see(tk.END)

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
                logger.info('  %s: %s (WORK IN PROGRESS, USE AT YOUR OWN RISK!)' % (format_combo(key), action_func_name))
            else:
                logger.info('  %s: %s' % (format_combo(key), action_func_name))

    def _print_help_shortcut(self):
        logger.trace('UI help')
        for key, action_func_name in sorted(self.action_map_keyboard.items()):
            if 'help' in action_func_name:
                logger.info('Press %s for "%s"' % (format_combo(key), action_func_name))

    def _cleanup_context_menu(self):
        if self._context_menu:
            self._context_menu.unpost()
            self._context_menu = None
            logger.trace('cleaning up context menu')
            return True
        return False

    def _render(self, width=None, height=None):
        t0 = time.time()
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
        self._base_color_depth = zoom_depth

        self.rects = self.compute_func(render_tree, [0, width], [0, height], self.config['tk_renderer'])
        for rect in self.rects:
            self._render_rect(rect, base_color_depth=zoom_depth)

        # Re-apply filter highlight if active
        filter_text = self.filter_entry.get().strip()
        if filter_text:
            self.highlighted_paths = set()  # Reset so _on_filter_change reapplies all
            self._on_filter_change()

        t1 = time.time()
        logger.info(f"{t1-t0:.6} sec to render")

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

        # Use trashed colors if this path has been trashed (trashed takes priority)
        is_trashed = rect['path'] in self.trashed_paths
        is_highlighted = rect['path'] in self.highlighted_paths
        if is_trashed:
            cs = self._trashed_color
            text_fill = self._trashed_text_color
        elif is_highlighted:
            cs = self._highlight_color
            text_fill = self._highlight_text_color
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

    def _find_rect(self, x, y, use_fallback=True):
        # TODO: it would be really nice if the rectangles and the tree nodes
        # were the same objects, so i could just traverse the tree right here...
        for rect in self.rects[::-1]:
            if rect['x'] <= x <= rect['x'] + rect['dx'] and rect['y'] <= y <= rect['y'] + rect['dy']:
                return rect
        # Fallback to last hovered rect (useful for keyboard actions from other windows)
        if use_fallback:
            return self._last_hovered_rect

    def _check_zoom_cooldown(self):
        """Returns True if zoom should proceed, False if in cooldown."""
        now = time.time()
        if now - self._last_zoom_time < self._zoom_cooldown:
            logger.trace('zoom cooldown, ignoring')
            return False
        self._last_zoom_time = now
        return True

    def _on_mousewheel(self, ev):
        if self._cleanup_context_menu():
            return
        logger.trace('mousewheel: %s' % ev)
        rect = self._find_rect(ev.x, ev.y)
        if rect:
            logger.trace('zooming on: "%s"' % (rect['path']))

    def _on_resize(self, ev):
        if self._cleanup_context_menu():
            return
        # Skip if size unchanged
        if ev.width == self.width and ev.height == self.height:
            return
        self.width, self.height = ev.width, ev.height
        # Debounce: cancel pending redraw and schedule new one
        if self._resize_job:
            self.master.after_cancel(self._resize_job)
        self._resize_job = self.master.after(100, self._do_render)

    def _do_render(self):
        self._resize_job = None
        logger.trace('resized: %d %d' % (self.width, self.height))
        self._render()

    def _on_hover(self, ev):
        rect = self._find_rect(ev.x, ev.y, use_fallback=False)
        if rect:
            self._last_hovered_rect = rect
            self.set_status(f"{rect['path']}  ({rect['bytes']})")
        else:
            self.set_status("Ready")

    def _on_canvas_click(self, ev):
        """Handle canvas click: steal focus from filter entry, then dispatch."""
        self.canv.focus_set()
        self._on_click(ev)

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
        if self.master.focus_get() == self.filter_entry:
            return
        if self._cleanup_context_menu():
            return
        key = ev.keysym
        logger.trace('keydown: "%s"' % key)

    def _on_keyup(self, ev):
        if self.master.focus_get() == self.filter_entry:
            return
        if self._cleanup_context_menu():
            return
        key = ev.keysym
        if key == 'slash':
            self.filter_entry.focus_set()
            return
        # Ignore modifier key releases
        if key in ('Alt_L', 'Alt_R', 'Control_L', 'Control_R',
                   'Shift_L', 'Shift_R', 'Super_L', 'Super_R',
                   'Meta_L', 'Meta_R', 'Caps_Lock', 'Num_Lock'):
            return
        s = ev.state
        logger.trace(f"keyup: keysym={key} state=0x{s:x}")
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
        if not rect:
            return
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
        # m.add_separator()
        # m.add_command(label="add to delete queue", underline=0, command=lambda: self.add_to_queue(ev, "delete"))
        # m.add_command(label="print queue", underline=0, command=lambda: self.print_queue(ev))
        # m.add_command(label="execute queue", underline=1, command=lambda: self.execute_queue(ev))
        #m.add_command(label="delete", underline=0, command=lambda: self.delete_file(ev))
        self._context_menu = m

        def on_menu_close():
            self._context_menu = None

        m.bind('<Unmap>', lambda e: on_menu_close())
        m.bind('<FocusOut>', lambda e: self._cleanup_context_menu())
        m.tk_popup(ev.x_root, ev.y_root)

    def quit(self, ev):
        sys.exit(0)

    def modifier_example(self, ev):
        logger.trace("forwarding example event")
        self.info(ev)

    def info(self, ev):
        logger.debug('  (%d, %d), (%d, %d)' %
              (ev.x, ev.y, ev.x_root, ev.y_root))
        rect = self._find_rect(ev.x, ev.y)
        if rect:
            logger.info('  %s (%s)' % (rect['path'], rect['bytes']))

    def refresh(self, ev):
        self.tree = self.scan_func()
        logger.trace('  refresh')
        self._render()

    def zoom_top(self, ev):
        # zooming can be a slow UI operation, should have at least one info-level log for each zoom action
        if not self._check_zoom_cooldown():
            return
        self.render_root = '/'
        logger.info("zoom top")
        self._render()

    def zoom_out(self, ev):
        # zooming can be a slow UI operation, should have at least one info-level log for each zoom action
        if not self._check_zoom_cooldown():
            return
        if self.render_root == '/':
            logger.info(f"not zooming above root node")
            return
        old_render_root = self.render_root
        parts = self.render_root.split('/')
        self.render_root = '/'.join(parts[:-1])
        if self.render_root == '':
            self.render_root = '/'
        logger.info(f"zoom out from {old_render_root} to {self.render_root}")
        self._render()

    def zoom_in(self, ev):
        # append one directory level to zoom state
        # zooming can be a slow UI operation, should have at least one info-level log for each zoom action
        if not self._check_zoom_cooldown():
            return
        old_render_root = self.render_root
        rect = self._find_rect(ev.x, ev.y)
        if not rect:
            return
        p1 = self.render_root
        parts1 = p1.split('/')
        p2 = rect['path'].lstrip(self.scan_root)
        parts2 = p2.split('/')
        if len(parts2) > len(parts1):
            parts2 = parts2[:len(parts1)+1]  # zoom in one level
        self.render_root = '/'.join(parts2)
        if self.render_root == old_render_root:
            logger.info("not zooming below leaf node")
            return

        # then render
        logger.info(f"zoom in from {old_render_root} to {self.render_root}")
        self._render()

    def cycle_mode(self, ev):
        logger.info('  cycle_mode: not yet implemented')
        # 0. total size
        # 1. total descendants

    def copy_path(self, ev):
        # https://unix.stackexchange.com/questions/139191/whats-the-difference-between-primary-selection-and-clipboard-buffer
        rect = self._find_rect(ev.x, ev.y)
        if not rect:
            return
        if pyperclip_present:
            pyperclip.copy(rect['path'])
            logger.info('  copied to clipboard: "%s"' % (rect['path']))
        else:
            logger.error('  copy_path: dependency `pyperclip` not available')
            logger.error('  install with: pip install pyperclip')

    def open_file(self, ev):
        rect = self._find_rect(ev.x, ev.y)
        if not rect:
            return
        logger.info('  open file: "%s"' % (rect['path']))
        open_file(rect['path'])

    def open_location(self, ev):
        rect = self._find_rect(ev.x, ev.y)
        if not rect:
            logger.trace("skip")
            return
        if rect['type'] == 'directory':
            location = rect['path']
            logger.trace(f"open dir: {location}")
        else:
            location = os.path.dirname(rect['path'])
            logger.trace(f"open parent: {location}")
        logger.info('  open location: "%s"' % location)
        open_file(location)

    def add_to_queue(self, ev, action):
        rect = self._find_rect(ev.x, ev.y)
        if not rect:
            return
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
        if not rect:
            return
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
        self.canv.itemconfig(items['rect_id'], fill=self._trashed_color[0])
        self.canv.itemconfig(items['highlight_id'], fill=self._trashed_color[1])
        self.canv.itemconfig(items['shadow_id'], fill=self._trashed_color[2])
        self.canv.itemconfig(items['text_id'], fill=self._trashed_text_color)
        return True

    def trash_path(self, ev):
        """Move file/folder to system trash and visually mark as trashed."""
        rect = self._find_rect(ev.x, ev.y)
        if not rect:
            return
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

    def show_help(self, ev):
        """Show a popup window with all keyboard and mouse shortcuts."""
        # Toggle: close if already open
        if self._help_window is not None:
            try:
                self._help_window.destroy()
            except:
                pass
            self._help_window = None
            return

        # Create help window
        help_win = tk.Toplevel(self.master)
        help_win.title("UI Actions")
        help_win.transient(self.master)  # Stay on top of main window

        # Position to the right of the main window
        main_x = self.master.winfo_x()
        main_y = self.master.winfo_y()
        main_width = self.master.winfo_width()
        help_win.geometry(f"400x650+{main_x + main_width + 10}+{main_y}")

        self._help_window = help_win

        def on_close():
            self._help_window = None
            help_win.destroy()

        help_win.protocol("WM_DELETE_WINDOW", on_close)
        help_win.bind('<Escape>', lambda e: on_close())

        # Forward keyboard events to main window handlers
        help_win.bind("<KeyPress>", self._on_keydown)
        help_win.bind("<KeyRelease>", self._on_keyup)

        # Create scrollable frame
        canvas = tk.Canvas(help_win, borderwidth=0)
        # scrollbar = tk.Scrollbar(help_win, orient="vertical", command=canvas.yview)
        content_frame = tk.Frame(canvas)

        # canvas.configure(yscrollcommand=scrollbar.set)
        # scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.create_window((0, 0), window=content_frame, anchor="nw")

        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        content_frame.bind("<Configure>", on_frame_configure)

        # Style
        header_font = ("Helvetica", 11, "bold")
        key_font = ("Courier", 10)
        action_font = ("Helvetica", 10)

        # Keyboard shortcuts section
        tk.Label(content_frame, text="Keyboard", font=header_font).pack(anchor="w", padx=10, pady=(10, 5))
        tk.Frame(content_frame, height=1, bg="gray").pack(fill=tk.X, padx=10, pady=2)

        for combo, action in sorted(self.action_map_keyboard.items(), key=lambda x: x[1]):
            row = tk.Frame(content_frame)
            row.pack(fill=tk.X, padx=10, pady=2)
            combo_str = format_combo(combo)
            tk.Label(row, text=combo_str, font=key_font, width=20, anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=action, font=action_font, anchor="w").pack(side=tk.LEFT, padx=10)

        # Mouse shortcuts section
        tk.Label(content_frame, text="Mouse", font=header_font).pack(anchor="w", padx=10, pady=(15, 5))
        tk.Frame(content_frame, height=1, bg="gray").pack(fill=tk.X, padx=10, pady=2)

        mouse_labels = get_mousebutton_names()

        for combo, action in sorted(self.action_map_mouse.items(), key=lambda x: x[1]):
            row = tk.Frame(content_frame)
            row.pack(fill=tk.X, padx=10, pady=2)
            combo_str = format_combo(combo)
            # Make mouse buttons more readable
            parts = list(combo)
            if len(parts) == 1 and parts[0] in mouse_labels:
                combo_str = mouse_labels[parts[0]]
            elif parts[-1] in mouse_labels:
                combo_str = '+'.join(parts[:-1]) + '+' + mouse_labels[parts[-1]]
            tk.Label(row, text=combo_str, font=key_font, width=20, anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=action, font=action_font, anchor="w").pack(side=tk.LEFT, padx=10)

        # Close hint
        tk.Label(content_frame, text="Esc to close", font=("Helvetica", 9, "italic"), fg="gray").pack(anchor="w", padx=10, pady=(15, 10))

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
