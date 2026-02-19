"""
Basic static SVG renderer for treemap visualization.

Generates a self-contained SVG file with rectangles and labels only —
no interactivity, no JavaScript.
"""

import html
from .colormap import colormap
from logger import logger


def render(scan_func, subdivide_func, config):
    """
    Generate a static SVG treemap.

    Args:
        tree: The directory tree structure
        compute_func: Function to compute rectangle layout
        config: Configuration dictionary
        output_path: Where to save the SVG file
        width: SVG width in pixels
        height: SVG height in pixels
        max_rects: Maximum number of rectangles to render (default 1000)
    """
    svg_params = config.get('svg-renderer', {})
    width = svg_params.get("width", 1200)
    height = svg_params.get("height", 800)
    max_rects = svg_params.get("max-rectangles", 1000)
    output_path = svg_params.get("filename")

    
    tree = scan_func()

    rects = subdivide_func(tree, [0, width], [0, height], config['svg-renderer'])

    if rects and len(rects) > max_rects:
        logger.warning("TODO: cull smallest rects only")
        rects = rects[:max_rects]

    svg_content = generate_svg(rects, width, height)

    with open(output_path, 'w') as f:
        f.write(svg_content)

    logger.info(f'SVG saved to: {output_path}')
    return output_path


def generate_svg(rects, width, height):
    """Generate a static SVG document with rectangles and text labels."""
    clip_defs, body = render_rects(rects)

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="{width}" height="{height}" viewBox="0 0 {width} {height}"
     style="background-color: #000000;">
  <defs>
    <style type="text/css">
      rect {{ stroke: #000000; stroke-width: 1; }}
      text {{
        font-family: Helvetica, Arial, sans-serif;
        font-size: 8px;
        fill: #000000;
        pointer-events: none;
      }}
    </style>
{clip_defs}
  </defs>
{body}
</svg>'''



def render_rects(rects):
    """Render a list of rect dicts to SVG elements.

    Returns (clip_defs, body) where clip_defs is a string of <clipPath>
    elements for <defs>, and body is the SVG shape/text elements.
    """
    clip_parts = []
    body_parts = []

    for i, rect in enumerate(rects):
        d = rect['depth'] % len(colormap)
        cs = colormap[d]

        x = rect['x']
        y = rect['y']
        dx = rect['dx']
        dy = rect['dy']

        # ClipPath matching this rect's bounds (1px inset to stay inside stroke)
        clip_id = f'c{i}'
        clip_parts.append(
            f'    <clipPath id="{clip_id}">'
            f'<rect x="{x+1}" y="{y+1}" width="{max(0, dx-2)}" height="{max(0, dy-2)}"/>'
            f'</clipPath>'
        )

        # Rectangle
        body_parts.append(
            f'  <rect x="{x}" y="{y}" width="{dx}" height="{dy}" fill="{cs[0]}"/>'
        )

        # Highlight lines (top/left lighter, bottom/right darker)
        body_parts.append(
            f'  <line x1="{x+1}" y1="{y+dy-1}" x2="{x+1}" y2="{y+1}" stroke="{cs[1]}" stroke-width="1"/>'
        )
        body_parts.append(
            f'  <line x1="{x+1}" y1="{y+1}" x2="{x+dx-1}" y2="{y+1}" stroke="{cs[1]}" stroke-width="1"/>'
        )
        body_parts.append(
            f'  <line x1="{x+1}" y1="{y+dy-1}" x2="{x+dx-1}" y2="{y+dy-1}" stroke="{cs[2]}" stroke-width="1"/>'
        )
        body_parts.append(
            f'  <line x1="{x+dx-1}" y1="{y+dy-1}" x2="{x+dx-1}" y2="{y+1}" stroke="{cs[2]}" stroke-width="1"/>'
        )

        # Text — left-aligned for both directories and files; clipPath clips the right
        text = html.escape(rect['text'])
        if rect['type'] == 'directory':
            body_parts.append(
                f'  <text x="{x + 3}" y="{y + 10}" text-anchor="start"'
                f' clip-path="url(#{clip_id})">{text}</text>'
            )
        else:
            body_parts.append(
                f'  <text x="{x + 3}" y="{y + dy / 2}" text-anchor="start"'
                f' dominant-baseline="middle" clip-path="url(#{clip_id})">{text}</text>'
            )

    return '\n'.join(clip_parts), '\n'.join(body_parts)
