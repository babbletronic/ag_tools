"""Rim joists own the perimeter; interior joists bear between the rims."""

import math
from .geometry import box
from .wood import board


def build(ctx, s):
    c = ctx.collections["Floor"]
    w = s.stud_width
    h = s.joist_depth
    z = s.foundation_height + h / 2
    for i, y in enumerate((-s.length / 2 + w / 2, s.length / 2 - w / 2)):
        box(ctx, f"floor.rim.end.{i}", (0, y, z), (s.width, w, h), c)
    for i, x in enumerate((-s.width / 2 + w / 2, s.width / 2 - w / 2)):
        box(ctx, f"floor.rim.side.{i}", (x, 0, z), (w, s.length - 2 * w, h), c)
    count = math.ceil((s.length - w) / s.joist_spacing)
    for i in range(1, count):
        y = -s.length / 2 + w / 2 + (s.length - w) * i / count
        box(ctx, f"floor.joist.{i:03}", (0, y, z), (s.width - 2 * w, w, h), c)
    n = math.ceil(s.width / (s.plank_width + s.plank_gap))
    width = (s.width - (n - 1) * s.plank_gap) / n
    for i in range(n):
        x = -s.width / 2 + width / 2 + i * (width + s.plank_gap)
        board(
            ctx,
            f"floor.board.{i:03}",
            s.length,
            width,
            s.floor_thickness,
            c,
            (x + width / 2, -s.length / 2, s.floor_z - s.floor_thickness / 2),
            (0, 1, 0),
            (-1, 0, 0),
        )
