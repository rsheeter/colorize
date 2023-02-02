from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.momentsPen import MomentsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen

from picosvg.svg_types import SVGPath
from picosvg import svg_pathops

# Records each subpath separately
#
# This is handy if you want to know things like which subpaths
# are "cut out" rather than filled.
class SubpathPen(BasePen):

    def __init__(self, glyphset=None):
        BasePen.__init__(self, glyphset)
        self.glyphset = glyphset
        self.recordings = []

    def moveTo(self, p0):
        self.recordings.append(DecomposingRecordingPen(self.glyphset))
        self.recordings[-1].moveTo(p0)

    def lineTo(self, p1):
        self.recordings[-1].lineTo(p1)
    def qCurveTo(self, *points):
        self.recordings[-1].qCurveTo(*points)
    def curveTo(self, *points):
        self.recordings[-1].curveTo(*points)
    def closePath(self):
        self.recordings[-1].closePath()
    def endPath(self):
        self.recordings[-1].endPath()
    def addComponent(self, glyphName, transformation):
        self.recordings[-1].addComponent(glyphName, transformation)

font = TTFont("Ewert-ABDQ.ttf")
glyphs = font.getGlyphSet()

for letter in "ABDQ":
#for letter in ("B"):
    glyph_name = font["cmap"].getBestCmap()[ord(letter)]

    whole_glyph_svg_pen = SVGPathPen(glyphs)
    glyphs[glyph_name].draw(whole_glyph_svg_pen)

    pen = SubpathPen(glyphs)
    glyphs[glyph_name].draw(pen)

    # Find the explicitly drawn negative shapes
    negatives = []
    areas = {}
    paths = []
    for recording in pen.recordings:
        svg_pen = SVGPathPen(glyphs)
        recording.replay(svg_pen)
        svg_path = SVGPath(d=svg_pen.getCommands())

        mpen = MomentsPen(glyphs)
        recording.replay(mpen)

        areas[svg_path.d] = mpen.area
        # this is weird, I thought it was supposed to be < 0
        if mpen.area > 0:
            negatives.append(svg_path)

            svg_path.fill = "green"
            svg_path.opacity = 0.75;

        else:
            paths.append(svg_path)

    # Sometimes there is a small cut-out, such as the inside of an A
    # We don't want to color those. Ewart's whole deal is a big upper
    # and a big lower so keep the two biggest negatives.
    negatives.sort(key=lambda p: -abs(areas[p.d]))

    # for negative in negatives:
    #     print("  ", negative)
    #     print("     ", areas[negative.d])

    # Distinguish the top shape from the bottom
    if len(negatives) >= 2:
        negatives = negatives[:2]
        negatives.sort(key=lambda n: n.bounding_box().y)
        negatives[0].fill = "darkblue"
        negatives[1].fill = "lightblue"

    paths = [SVGPath(d=whole_glyph_svg_pen.getCommands())] + negatives

    print()
    print("""<svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="0 0 1024 1024">""")
    print("""<g transform="matrix(1 0 0 -1 0 800)">""")
    for path in paths:
        print("  ", path)
    print("</svg>")
    print()
