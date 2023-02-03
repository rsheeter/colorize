from functools import cache

from fontTools.pens.basePen import AbstractPen, BasePen
from fontTools.pens.basePen import BasePen
from fontTools.pens.momentsPen import MomentsPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import getTableModule, TTFont
from picosvg.geometric_types import Rect
from picosvg.svg_types import SVGPath

def color(hex: str):
  return getTableModule('CPAL').Color.fromHex(hex)


def make_glyph_name(glyph_name, nth):
    return f"{glyph_name}_{nth}"


@cache
def bbox(path: str) -> Rect:
    return SVGPath(d=path).bounding_box()


def draw(svg_path: SVGPath, pen: AbstractPen):
    for cmd in svg_path.as_cmd_seq():
        match cmd:
            case ("M", pt):
                pen.moveTo(pt)
            case ("L", pt):
                pen.lineTo(pt)
            case ("Q", (x1, y1, x, y)):
                pen.qCurveTo((x1, y1), (x, y))
            case ("Z", ()):
                pen.closePath()
            case _:
                raise ValueError(f"TODO {cmd}")


def make_glyph(font: TTFont, original_glyph_name: str, new_glyph_name: str, path: SVGPath):
    assert new_glyph_name not in font.getGlyphOrder(), new_glyph_name

    glyphs = font.getGlyphSet()
    glyph_pen = TTGlyphPen(glyphs)
    draw(path, glyph_pen)
    new_glyph = glyph_pen.glyph()

    # Adding a glyph is surprisingly tricksy
    font.getGlyphOrder().append(new_glyph_name)
    glyf = font["glyf"]
    glyf.glyphs[new_glyph_name] = new_glyph
    new_glyph.recalcBounds(glyf)
    # Copy advance, use our own xMin
    font["hmtx"].metrics[new_glyph_name] = (font["hmtx"].metrics[original_glyph_name][0], new_glyph.xMin)


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
        self.recordings.append(DecomposingRecordingPen(self.glyphset))
        self.recordings[-1].addComponent(glyphName, transformation)