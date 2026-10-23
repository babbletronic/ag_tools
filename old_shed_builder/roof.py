"""Gable roof: notched rafters, ridge board, ties and two distinct roof skins."""

import math
from .geometry import box, member, prism
from .model import wall_point
from .wood import board
from mathutils import Vector


def build(ctx, s):
    c = ctx.collections["Roof.Framing"]
    cover = ctx.collections["Roof.Covering"]
    half = s.width / 2
    k = math.tan(math.radians(s.roof_pitch))
    cosine = math.cos(math.radians(s.roof_pitch))
    top = s.floor_z + s.wall_height

    def bottom(x):
        return top + k * (half - s.stud_depth - x)

    thick = s.rafter_depth / cosine
    inner = s.ridge_thickness / 2
    outer = half + s.overhang
    ridge_top = bottom(inner) + thick
    box(
        ctx,
        "roof.ridge",
        (0, 0, ridge_top - (thick + 0.04) / 2),
        (s.ridge_thickness, s.length + 2 * s.overhang, thick + 0.04),
        c,
    )
    n = math.ceil((s.length - s.stud_depth) / s.rafter_spacing)
    positions = [
        -s.length / 2 + s.stud_depth / 2 + (s.length - s.stud_depth) * i / n
        for i in range(n + 1)
    ]
    positions = (
        [-s.length / 2 - s.overhang + s.stud_width / 2]
        + positions
        + [s.length / 2 + s.overhang - s.stud_width / 2]
    )
    for j, y in enumerate(positions):
        for sign in (-1, 1):
            # Birdsmouth seats only over bearing walls; fly rafters have no notch.
            if 0 < j < len(positions) - 1:
                lower = [
                    (inner, bottom(inner)),
                    (half - s.stud_depth, top),
                    (half, top),
                    (half, bottom(half)),
                    (outer, bottom(outer)),
                ]
            else:
                lower = [(inner, bottom(inner)), (outer, bottom(outer))]
            profile = [
                (sign * x, z)
                for x, z in lower + [(outer, bottom(outer) + thick), (inner, ridge_top)]
            ]
            obj = prism(ctx, f"roof.rafter.{j:03}.{sign}", profile, s.stud_width, c)
            obj.location.y = y
        if s.collar_ties and 0 < j < len(positions) - 1:
            x = half * 0.38
            z = bottom(x) + thick * 0.35
            box(
                ctx,
                f"roof.collar.{j:03}",
                (0, y + s.stud_width, z),
                (2 * x, s.stud_width, s.rafter_depth * 0.65),
                c,
            )
    for wall in ("Front", "Rear"):
        wc = ctx.collections[wall + ".Framing"]
        n = math.ceil((s.width - 2 * s.stud_depth) / s.stud_spacing)
        for i in range(1, n):
            x = -half + s.stud_depth + (s.width - 2 * s.stud_depth) * i / n
            high = bottom(abs(x) + s.stud_width / 2)
            if high > top + 0.01:
                box(
                    ctx,
                    f"{wall}.gable.stud.{i:03}",
                    wall_point(s, wall, x + half, (top + high) / 2),
                    (s.stud_width, s.stud_depth, high - top),
                    wc,
                )
    # Sheathing planks run eave to ridge; roof boards run along Y on top.
    for sign in (-1, 1):
        a = (sign * inner, 0, ridge_top)
        b = (sign * outer, 0, bottom(outer) + thick)
        if s.sheathing:
            n = math.ceil((s.length + 2 * s.overhang) / s.plank_width)
            width = (s.length + 2 * s.overhang) / n
            for i in range(n):
                y = -s.length / 2 - s.overhang + (i + 0.5) * width
                sine = math.sin(math.radians(s.roof_pitch))
                board(
                    ctx,
                    f"roof.sheathing.{sign}.{i:03}",
                    (outer - inner) / cosine,
                    width - 0.001,
                    0.018,
                    cover,
                    (a[0], y - sign * (width - 0.001) / 2, a[2] + 0.009 / cosine),
                    (sign * cosine, 0, -sine),
                    (0, sign, 0),
                )
        slope = (outer - inner) / cosine
        count = math.ceil(slope / s.plank_width)
        pitch = slope / count
        for i in range(count):
            x = inner + (i + 0.5) * (outer - inner) / count
            z = (
                bottom(x)
                + thick
                + (0.018 if s.sheathing else 0) / cosine
                + s.plank_thickness / 2 / cosine
            )
            u = Vector((0, 1, 0))
            v = Vector((-cosine, 0, sign * math.sin(math.radians(s.roof_pitch))))
            length = s.length + 2 * s.overhang
            width = pitch - 0.002
            origin = Vector((sign * x, 0, z)) - u * length / 2 - v * width / 2
            board(
                ctx,
                f"roof.cover.board.{sign}.{i:03}",
                length,
                width,
                s.plank_thickness,
                cover,
                origin,
                u,
                v,
            )
