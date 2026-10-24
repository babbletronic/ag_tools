"""Horizontal solid boards cut exactly at rough openings and gable roof lines."""

import math
from .model import WALLS, subtract, wall_point
from .wood import board, rng_for


def build(ctx, s):
    for wall in WALLS:
        span = s.span(wall)
        c = ctx.collections[wall + ".Cladding"]
        k = math.tan(math.radians(s.roof_pitch))
        gable = wall in ("Front", "Rear")
        # Close gable up to sheathing; notch side boards around penetrating rafters.
        roof_thickness = s.rafter_depth / math.cos(math.radians(s.roof_pitch))
        height = s.wall_height + (
            (s.width / 2 - s.stud_depth) * k + roof_thickness
            if gable
            else roof_thickness - (s.stud_depth + s.plank_thickness) * k
        )
        obstacles = [
            (
                o.position - o.width / 2,
                o.position + o.width / 2,
                o.bottom,
                o.bottom + o.height,
            )
            for _, o in s.openings(wall)
        ]
        if gable:
            ridge_bottom = (
                s.wall_height
                + k * (s.width / 2 - s.stud_depth - s.ridge_thickness / 2)
                - 0.04
            )
            obstacles.append(
                (
                    span / 2 - s.ridge_thickness / 2,
                    span / 2 + s.ridge_thickness / 2,
                    ridge_bottom,
                    height,
                )
            )
        else:
            n = math.ceil((s.length - s.stud_depth) / s.rafter_spacing)
            for i in range(n + 1):
                pos = s.stud_depth / 2 + (s.length - s.stud_depth) * i / n
                obstacles.append(
                    (
                        pos - s.stud_width / 2 - 0.002,
                        pos + s.stud_width / 2 + 0.002,
                        s.wall_height - k * (s.stud_depth + s.plank_thickness) - 0.002,
                        height,
                    )
                )
        leakage = s.leak(wall)
        use_leakage = getattr(ctx, "stage", 10) >= 8
        amount = leakage.amount * (1.8 if s.dramatic else 1) if use_leakage else 0
        row = 0
        bottom = 0
        while bottom < height - 0.001:
            upper = min(bottom + s.plank_width, height)
            cuts_z = sorted(
                set(
                    [bottom, upper]
                    + [
                        z
                        for a, b, low, high in obstacles
                        for z in (low, high)
                        if bottom < z < upper
                    ]
                )
            )
            for part, (low, high) in enumerate(zip(cuts_z, cuts_z[1:])):
                cuts = [
                    (a, b)
                    for a, b, zmin, zmax in obstacles
                    if low < zmax - 1e-6 and high > zmin + 1e-6
                ]
                l, r = 0, span
                if gable and low > s.wall_height + roof_thickness - k * s.stud_depth:
                    reach = (low - s.wall_height - roof_thickness) / k + s.stud_depth
                    l, r = reach, span - reach
                for seg, (a, b) in enumerate(subtract((l, r), cuts)):
                    if b - a < 0.01:
                        continue
                    fit_a, fit_b = a, b
                    inset = min(0.005, (b - a) * 0.02) * s.crooked
                    a += inset
                    b -= inset
                    top = None
                    breaks = []
                    if gable and high > s.wall_height:

                        def top(x, a=a, low=low, high=high):
                            roof = (
                                s.wall_height
                                + roof_thickness
                                + k
                                * (
                                    s.width / 2
                                    - s.stud_depth
                                    - abs(a + x - s.width / 2)
                                )
                            )
                            return max(0.0001, min(high, roof) - low)

                        for u in (
                            span / 2,
                            s.stud_depth + (high - s.wall_height - roof_thickness) / k,
                            span
                            - s.stud_depth
                            - (high - s.wall_height - roof_thickness) / k,
                        ):
                            if a < u < b:
                                breaks.append(u - a)
                    # Reverse the local axis on rear/left to keep outward normals.
                    reverse = wall in ("Rear", "Left")
                    local_a = b if reverse else a
                    origin = wall_point(
                        s,
                        wall,
                        local_a,
                        s.floor_z + low,
                        s.stud_depth / 2 + s.plank_thickness / 2,
                    )
                    u = (1, 0, 0) if wall in ("Front", "Rear") else (0, 1, 0)
                    if reverse:
                        u = tuple(-x for x in u)
                    if top and reverse:
                        fn = top
                        top = lambda x, fn=fn: fn(b - a - x)
                        breaks = [b - a - x for x in breaks]
                    key = f"{wall}.siding.{row:03}.{part}.{seg}"
                    rng = rng_for(s.leak_seed, key)
                    if rng.random() < min(0.9, leakage.missing * amount):
                        continue
                    obj = board(
                        ctx,
                        f"{wall}.siding.{row:03}.{part}.{seg}",
                        b - a,
                        high - low,
                        s.plank_thickness,
                        c,
                        origin,
                        u,
                        (0, 0, 1),
                        top=top,
                        breaks=breaks,
                    )
                    obj["shed_wall"] = wall
                    obj["shed_course"] = row
                    obj["shed_plan_bounds"] = [fit_a, fit_b, low, high]
                    obj["shed_roof_limit"] = [
                        height,
                        k if gable else 0,
                        s.wall_height
                        + roof_thickness
                        + k * (s.width / 2 - s.stud_depth),
                    ]
                    obj["shed_openings"] = [
                        value for obstacle in obstacles for value in obstacle
                    ]
                    obj["shed_reverse"] = reverse
                    obj["shed_leak_loose"] = rng.random() < min(
                        0.9, leakage.loose * amount
                    )
                    obj["shed_leak_separation"] = min(0.15, leakage.separation * amount)
                    # Nail positions follow actual studs/jacks at this elevation.
                    points = []
                    for support in ctx.collections[wall + ".Framing"].objects:
                        key = support.get("shed_key", "")
                        if not any(
                            t in key
                            for t in (".stud.", ".king.", ".jack.", ".cripple.")
                        ):
                            continue
                        u_support = (
                            support.location.x + s.width / 2
                            if wall in ("Front", "Rear")
                            else support.location.y + s.length / 2
                        )
                        z_support = s.floor_z + (low + high) / 2
                        zmin = (
                            min(v.co.z for v in support.data.vertices)
                            + support.location.z
                        )
                        zmax = (
                            max(v.co.z for v in support.data.vertices)
                            + support.location.z
                        )
                        if a <= u_support <= b and zmin <= z_support <= zmax:
                            points.append(b - u_support if reverse else u_support - a)
                    if points:
                        obj["shed_supports"] = sorted(points)

            gap = course_gap(s, wall, row, leakage, amount)
            bottom = upper + gap
            row += 1


def course_gap(s, wall, row, leakage=None, amount=None):
    """Weighted bounded spacing; full randomization ranges from zero to max."""
    leakage = leakage or s.leak(wall)
    if amount is None:
        amount = leakage.amount * (1.8 if s.dramatic else 1)
    rng = rng_for(s.leak_seed, f"{wall}.gap.{row}")
    sample = rng.random() ** (1 / s.gap_weight)
    ordinary = s.plank_gap + leakage.gap * amount * (
        1 + (2 * sample - 1) * leakage.variation
    )
    maximum = s.plank_gap + leakage.gap * amount * (1 + leakage.variation)
    if rng.random() < leakage.large_probability * amount:
        ordinary += s.plank_width * 0.22 * amount
        maximum += s.plank_width * 0.22 * amount
    cap = s.plank_width * (0.65 if s.dramatic else 0.35)
    return max(
        0,
        min(cap, ordinary) * (1 - s.gap_randomizer)
        + min(cap, maximum) * sample * s.gap_randomizer,
    )
