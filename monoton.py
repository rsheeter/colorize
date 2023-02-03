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




font = TTFont("../fonts/ofl/monoton/Monoton-Regular.ttf")
#font = TTFont("./Akronim-ABY.ttf")

glyphs = font.getGlyphSet()
glyf = font["glyf"]

cpal = font["CPAL"] = newTable("CPAL")
cpal.version = 1
cpal.palettes = [
    [color('#d91111FF'), color('#d9d511FF'), color('#11d9d5FF'), color('#1b11d9FF'), color('#d911cbFF')],
    [color('#040db8FF'), color('#484db0FF'), color('#236db8FF'), color('#2395b8FF'), color('#23b8aeFF')],
]
# Why would you make me set this?!
cpal.numPaletteEntries = len(cpal.palettes[0])

foreground = {
    "Format": ot.PaintFormat.PaintSolid,
    "PaletteIndex": 0xFFFF,
    "Alpha": 1.0
}

colrv1 = {}
areas = {"": 0}
visited = set()
for cp, glyph_name in font["cmap"].getBestCmap().items():
    if glyph_name in visited:
        print("skip", chr(cp))
        continue
    visited.add(glyph_name)
    print(chr(cp))
    whole_glyph_svg_pen = SVGPathPen(glyphs)
    glyphs[glyph_name].draw(whole_glyph_svg_pen)

    pen = SubpathPen(glyphs)
    glyphs[glyph_name].draw(pen)

    paths = []
    negatives = []
    for i, recording in enumerate(pen.recordings):
        svg_pen = SVGPathPen(glyphs)
        recording.replay(svg_pen)
        svg_path = SVGPath(d=svg_pen.getCommands())

        mpen = MomentsPen(glyphs)
        recording.replay(mpen)

        areas[svg_path.d] = mpen.area
        # this is weird, I thought it was supposed to be < 0
        if mpen.area > 0:
            negatives.append(svg_path)
        else:
            paths.append(svg_path)

    paths.sort(key=lambda p: -abs(areas[p.d]))
    for path, color in zip(paths, cpal.palettes[0]):
        path.fill = color

    layers = []

    # Color the parts we find
    for i, path in enumerate(paths):
        # glue on the largest negative we can find that is contained by path
        biggest_negative = SVGPath()
        for negative in negatives:
            if bbox(path.d).intersection(bbox(negative.d)) != bbox(negative.d):
                continue
            if areas[biggest_negative.d] < areas[negative.d]:
                biggest_negative = negative

        path.d += biggest_negative.d

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

font.save("Monoton-Spice.ttf")