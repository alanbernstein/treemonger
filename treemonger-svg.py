#!/usr/local/bin/python
import sys
import os
import socket
import multiprocessing
import webbrowser
import SimpleHTTPServer
import SocketServer

from scan import get_directory_tree, print_directory_tree, tree_to_dict
from subdivide import compute_rectangles
from renderers.svg import render as render_svg


# from panda.debug import jprint

# plan
# - scan filesystem and create JSON file with full treemap definition
#   - more or less the same algorithm as before
# - start local server and open html page that handles the interface (very simple)
# - html page loads json file from local server
#   - this is new to me, but very similar to mike bostock d3.js examples


PORT = 8000
PAGE_FILENAME = 'treemap-nested.html'
DATA_FILENAME = 'treemap.json'


def main(args):
    if len(args) < 2:
        print('using pwd')
        root = '.'
    else:
        root = args[1]

    t = get_directory_tree(root)

    data = {'tree': tree_to_dict(t),
            'root': os.path.realpath(root),
            'host': os.getenv('MACHINE', socket.gethostname())}

    width = 800
    height = 600
    rects = compute_rectangles(t, [0, width], [0, height])
    render_svg(rects)

    open_result_in_browser(PORT, PAGE_FILENAME)


class SimpleServer(multiprocessing.Process):
    def run(self):
        Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
        httpd = SocketServer.TCPServer(("", PORT), Handler)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('server stopped')


def open_result_in_browser(port, path):
    httpd = SimpleServer()
    httpd.start()
    webbrowser.open("http://localhost:%s/%s" % (port, path))


if __name__ == '__main__':
    main(sys.argv)
