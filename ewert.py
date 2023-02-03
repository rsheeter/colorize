
from fontTools.colorLib import builder
from fontTools.ttLib import newTable, TTFont
from fontTools.ttLib.tables import otTables as ot
from fontTools.pens.svgPathPen import SVGPathPen


from picosvg import svg_pathops
from picosvg.svg_types import SVGPath

from helpers import *


_RETAIN_WIDEST = {
    "D": 2,
    "N": 3,
    "O": 2,
    "Q": 2,
    "0": 2,
}


font = TTFont("../fonts/ofl/ewert/Ewert-Regular.ttf")
#font = TTFont("./Ewert-QOD.ttf")

glyphs = font.getGlyphSet()
glyf = font["glyf"]

cpal = font["CPAL"] = newTable("CPAL")
cpal.version = 1
cpal.palettes = [
    [color('#C90900FF'), color('#FF9580FF')],
    [color('#FFD214FF'), color('#FF552DFF')],
    [color('#FF1471FF'), color('#780082FF')],
    [color('#00A0E1FF'), color('#2200F5FF')],
    [color('#5A5A78FF'), color('#141432FF')],
    [color('#C3C3E1FF'), color('#555573FF')],
    [color('#FFD700FF'), color('#00A050FF')],
    [color('#3C148CFF'), color('#D20050FF')],
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
    #print(chr(cp))
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
        else:
            paths.append(svg_path)

    # Ewart has cut-outs up high and cut-outs down low
    # so collect uppers and lowers
    uppers = []
    lowers = []
    split_y = 275
    for negative in negatives:
        box = bbox(negative.d)

        y_above = max(box.y, split_y)
        above = Rect(box.x, y_above, box.w, max(max(box.y + box.h, split_y) - y_above, 0))
        area_above = above.w * above.h
        area_below = box.w * box.h - area_above

        if area_above > area_below:
            uppers.append(negative)
        else:
            lowers.append(negative)

    # Hack: throw out all but the N widest negatives for these glyphs
    # Gets rid of the inside of O, the nook under th eN, etc
    retain_n_widest = _RETAIN_WIDEST.get(chr(cp).upper(), 0)
    if retain_n_widest > 0:
        widest = set(sorted(set(bbox(n.d).w for n in negatives), reverse=True)[:retain_n_widest])
        drops = []
        for i, n in enumerate(negatives):
            if not bbox(n.d).w in widest:
                drops.append(i)
        drops = sorted(set(drops), reverse=True)
        for i in drops:
            negatives.pop(i)

    # Cut contained paths away from negatives so they don't cover things like
    # the hole in an A
    for negative in negatives:
        for path in paths:
            if bbox(negative.d).intersection(bbox(path.d)) == bbox(path.d):
                fixed = SVGPath.from_commands(
                    svg_pathops.difference(
                        [negative.as_cmd_seq(), path.as_cmd_seq()],
                        [negative.fill_rule, path.fill_rule],
                    )
                )
                negative.d = fixed.d

    # Throw out negatives whose bbox is contained by that of others
    # This is meant to drop things like the counter within the loop of a P
    # or the nook under the diagonal of the N
    drops = []
    for n in negatives:
        for i, n2 in enumerate(negatives):
            if n == n2:
                continue
            if bbox(n.d).intersection(bbox(n2.d)) == bbox(n2.d):
                drops.append(i)
    drops = sorted(set(drops), reverse=True)
    for i in drops:
        negatives.pop(i)

    layers = [
        {
            "Format": ot.PaintFormat.PaintGlyph,
            "Paint": foreground,
            "Glyph": glyph_name,
        },
    ]

    # Create new glyphs for negatives so we can color them
    for i, negative in enumerate(negatives):
        new_glyph_name = make_glyph_name(glyph_name, i)
        make_glyph(font, glyph_name, new_glyph_name, negative)

        palette_index = 0
        if negative in lowers:
            palette_index = 1

        negative.fill = cpal.palettes[0][palette_index]

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

    # Dump svg for debugging
    paths = [SVGPath(d=whole_glyph_svg_pen.getCommands().replace("M", "\nM"))] + negatives

    svg_paths = "\n      ".join(str(p) for p in paths)

    svg = f"""
    <!-- {chr(cp)} => {glyph_name} -->
    <svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="0 0 1024 1024">
    <g transform="matrix(1 0 0 -1 0 800)">
    {svg_paths}
    </g>
    </svg>
    """
    with open(f"ewert_{glyph_name}.svg", "w") as f:
        f.write(svg)

font["COLR"] = builder.buildCOLR(colrv1)

font.save("fonts/ewert/Ewert-Spice.ttf")