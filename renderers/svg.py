# combine functionality from all of these (most important first:
# - https://bost.ocks.org/mike/treemap/ - click to zoom
# - https://bl.ocks.org/mbostock/911ad09bdead40ec0061 - nesting
# - https://bl.ocks.org/mbostock/6645441 - padding
# - https://bl.ocks.org/mbostock/4063582 - size/count switch
#
# more stuff https://bl.ocks.org/mbostock
#
# https://madebymike.com.au//writing/svg-has-more-potential/
# https://news.ycombinator.com/item?id=12583509
# https://upload.wikimedia.org/wikipedia/commons/e/e0/Sexagenary_cycle_years.svg
# https://en.wikipedia.org/wiki/User:Cmglee/Dynamic_SVG_for_Wikimedia_projects


# - redo GUI
#   - SVG ala flame graph? (uses SMIL which was deprecated in chrome 2015, prefer something more future proof)
#     - related but different: http://tympanus.net/codrops/2014/08/19/making-svgs-responsive-with-css/
#     - http://stackoverflow.com/questions/30965580/deprecated-smil-svg-animation-replaced-with-css-or-web-animations-effects-hover
#     - https://github.com/webframes/smil2css
#     - check up on flamegraph in a while and see if they've figured out an alternative - https://github.com/brendangregg/FlameGraph
#   - js somehow... dont really want to use a pure js library because of the volume of data that is fundamentally local...
#   - some more modern, native python gui lib
#     - bokeh
#       - interactive, modern, intended for use with large/streaming data sets
#       - good opportunity to make the layout algorithm capable of dynamic/updating
#       - not obvious how to do a treemap or generally custom plot
#     - vincent - "data processing of python, visualization of js"
#       - not obvious how to do treemaps directly
#   - d3.js
#
# OR - just output json, and send it to a d3-based js page
# https://bost.ocks.org/mike/treemap/
# https://bl.ocks.org/mbostock/4063582
# http://bl.ocks.org/ganeshv/6a8e9ada3ab7f2d88022
# http://www.billdwhite.com/wordpress/2012/12/16/d3-treemap-with-title-headers/


def render(rects, width, height):
    pass
