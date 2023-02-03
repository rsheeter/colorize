from functools import cache
from fontTools.colorLib import builder
from fontTools.ttLib import newTable, TTFont
from fontTools.ttLib.tables import otTables as ot
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.momentsPen import MomentsPen

from picosvg.svg_types import SVGPath
from picosvg import svg_pathops
from picosvg.geometric_types import Rect

from helpers import *


_RETAIN_WIDEST = {
    "D": 2,
    "N": 3,
    "O": 2,
    "Q": 2,
    "0": 2,
}




font = TTFont("../fonts/ofl/akronim/Akronim-Regular.ttf")
#font = TTFont("./Akronim-ABY.ttf")

glyphs = font.getGlyphSet()
glyf = font["glyf"]

cpal = font["CPAL"] = newTable("CPAL")
cpal.version = 1
cpal.palettes = [
    [color('#040db8FF'), color('#484db0FF'), color('#236db8FF'), color('#2395b8FF'), color('#23b8aeFF')],
    [color('#C90900FF'), color('#f58d05FF'), color('#f5ed05FF'), color('#992811FF'), color('#b86404FF')],
    [color('#c90057FF'), color('#b200c9FF'), color('#e01fc3FF'), color('#8b14baFF'), color('#bf2a75FF')],
]
# Why would you make me set this?!
cpal.numPaletteEntries = len(cpal.palettes[0])

foreground = {
    "Format": ot.PaintFormat.PaintSolid,
    "PaletteIndex": 0xFFFF,
    "Alpha": 1.0
}

colrv1 = {}

for cp, glyph_name in font["cmap"].getBestCmap().items():
    print(chr(cp))
    whole_glyph_svg_pen = SVGPathPen(glyphs)
    glyphs[glyph_name].draw(whole_glyph_svg_pen)

    pen = SubpathPen(glyphs)
    glyphs[glyph_name].draw(pen)

    areas = {"": 0}
    paths = []
    negatives = []
    for i, recording in enumerate(pen.recordings):
        svg_pen = SVGPathPen(glyphs)
        recording.replay(svg_pen)
        svg_path = SVGPath(d=svg_pen.getCommands())

        mpen = MomentsPen(glyphs)
        recording.replay(mpen)

        areas[svg_path.d] = mpen.area
        paths.append(svg_path)

    paths.sort(key=lambda p: -abs(areas[p.d]))
    for path, color in zip(paths, cpal.palettes[0]):
        path.fill = color

    layers = []

    # Color the parts we find
    for i, path in enumerate(paths):
        new_glyph_name = make_glyph_name(glyph_name, i)
        make_glyph(font, glyph_name, new_glyph_name, path)

        palette_index = i % len(cpal.palettes[0])

        layers.append({
            "Format": ot.PaintFormat.PaintGlyph,
            "Paint": {
                "Format": ot.PaintFormat.PaintSolid,
                "PaletteIndex": palette_index,
                "Alpha": 1.0
            },
            "Glyph": new_glyph_name,
        })

    colrv1[glyph_name] = (ot.PaintFormat.PaintColrLayers, layers)

    svg_paths = "\n      ".join(str(p) for p in paths)
    svg = f"""
    <!-- {chr(cp)} => {glyph_name} -->
    <svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="0 0 1024 1024">
    <g transform="matrix(1 0 0 -1 0 800)">
    {svg_paths}
    </g>
    </svg>
    """
    with open(f"akronim_{glyph_name}.svg", "w") as f:
        f.write(svg)

font["COLR"] = builder.buildCOLR(colrv1)

font.save("fonts/akronim/Akronim-Spice.ttf")