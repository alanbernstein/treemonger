from utils import format_bytes

"""
using, for example, the squarify module is an appealing idea
but since i want to handle files and directories differently, i'm
not sure if there is a clean way to use something else

https://github.com/laserson/squarify
"""


def compute_rectangles(node, xlim, ylim, params, recurse_level=0, dir_level=0, rects=[]):
    # this function has to handle 3 cases:
    #  - single file: return a single rect
    #  - full directory: return single rect, divide and recurse on child files
    #  - "file group": return no rect, divide and recurse on child files
    #
    # tree.path
    # tree.size
    # tree.children = [tree, tree, ...]

    # TODO: need to enforce append order of rects such that
    #       drawing in iteration order ensures proper z ordering

    if (dir_level > params['max_filesystem_depth'] or
        xlim[1] - xlim[0] < params['min_box_size'] or
        ylim[1] - ylim[0] < params['min_box_size'] or
        type(node) is not list and 'hide' in node.details):
        return

    if type(node) == list:
        node_type = 'file_group'
    elif len(node.children) > 0:
        node_type = 'directory'
    else:
        node_type = 'file'

    if node_type in ['directory', 'file']:
        # - define a box and text
        # - if directory, compute new padded bounds for child boxes
        txt = node.path if recurse_level == 0 else node.name
        txt += ' (%s)' % format_bytes(node.size)

        rect = {'x': xlim[0] + 1,
                'y': ylim[0] + 1,
                'dx': xlim[1] - xlim[0],
                'dy': ylim[1] - ylim[0],
                'depth': dir_level,
                'bytes': format_bytes(node.size),
                'text': txt,
                'type': node_type,
                'path': node.path,
                }
        rects.append(rect)

        if node_type == 'directory':
            # directory padding
            ylim[0] = ylim[0] + params['text_size'] + params['dir_text_offset']
            ylim[1] = ylim[1] - 3
            xlim[0] = xlim[0] + 3
            xlim[1] = xlim[1] - 3

    if node_type in ['file_group', 'directory']:
        # - divide children into nearly equal parts,
        # - recurse on both halves

        if node_type == 'directory':
            children = node.children
            subdir_level = 1
            total_size = node.size
        else:
            children = node
            subdir_level = 0
            total_size = sum([x.size for x in node])

        groupA, xA, yA, groupB, xB, yB = squarify(children, xlim, ylim, params['xpad'], params['ypad'], total_size=total_size)

        # recurse
        compute_rectangles(groupA, xA, yA, params, recurse_level + 1,
                           dir_level + subdir_level)
        compute_rectangles(groupB, xB, yB, params, recurse_level + 1,
                           dir_level + subdir_level)

    return rects


def squarify(nodes, xlim, ylim, xpad, ypad, total_size):
    """core geometric subdivision algorithm
    given:
    - a list of nodes, each with a 'size' attribute,
    - bounding rectangle
    do this:
    - sort list by size
    - split list into halves as nearly equally as possible
    - split rectangle proportionately
      - vertically if wide
      - horizontally if tall
    - if either half has a single element, pull out of list
    """

    nodes.sort(key=lambda x: x.size)

    Asize = 0
    split = 0
    while Asize < total_size / 2:
        Asize = Asize + nodes[split].size
        split += 1
    if split == len(nodes):
        split -= 1
        Asize = Asize - nodes[split].size

    # split into two groups, append extra information
    groupA = nodes[0:split]
    groupB = nodes[split:]

    # figure out geometric division
    if xlim[1] - xlim[0] > ylim[1] - ylim[0]:
        # wide box - divide left/right
        xdiv = xlim[0] + (xlim[1] - xlim[0]) * Asize / total_size
        xA = [xlim[0], xdiv]
        xB = [xdiv, xlim[1]]
        yA = ylim
        yB = ylim
    else:
        # tall box - divide top/bottom
        ydiv = ylim[0] + (ylim[1] - ylim[0]) * Asize / total_size
        xA = xlim
        xB = xlim
        yA = [ylim[0], ydiv]
        yB = [ydiv, ylim[1]]

    # extract single element if necessary; add some graphical padding
    if len(groupA) == 1:
        groupA = groupA[0]
        xA = [xA[0] + xpad, xA[1] - xpad]
        yA = [yA[0] + ypad, yA[1] - ypad]
    if len(groupB) == 1:
        groupB = groupB[0]
        xB = [xB[0] + xpad, xB[1] - xpad]
        yB = [yB[0] + ypad, yB[1] - ypad]

    return groupA, xA, yA, groupB, xB, yB
