import matplotlib.pyplot as plt

from .colormap import colormap


def render(rects):
    for rect in rects:
        x = rect['x']
        y = rect['y']
        dx = rect['dx']
        dy = rect['dy']
        c = colormap[rect['depth']][0]
        xvec = [x, x+dx, x+dx, x, x]
        yvec = [y, y, y+dy, y+dy, y]
        plt.plot(xvec, yvec, c)

    plt.show()
