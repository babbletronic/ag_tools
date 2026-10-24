"""Fit rigid in-plane siding rotations into the actual neighboring board gaps.

Convex projected silhouettes give conservative clearances even after bow, twist,
and end damage. A small end fitting allowance is reserved by cladding.build.
The deterministic sequential solve never moves a previously fitted board.
"""

import math
from .wood import rng_for

EPS = 0.0001


def hull(points):
    points = sorted(set(points))
    if len(points) < 3:
        return points

    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    lower = []
    for p in points:
        while len(lower) > 1 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(points):
        while len(upper) > 1 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def bounds_at(poly, x):
    values = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if min(a[0], b[0]) - 1e-8 <= x <= max(a[0], b[0]) + 1e-8:
            if abs(a[0] - b[0]) < 1e-10:
                values.extend((a[1], b[1]))
            else:
                t = (x - a[0]) / (b[0] - a[0])
                values.append(a[1] + t * (b[1] - a[1]))
    return (min(values), max(values)) if values else None


def clearance(a, b, above):
    left = max(min(p[0] for p in a), min(p[0] for p in b))
    right = min(max(p[0] for p in a), max(p[0] for p in b))
    if right - left < 1e-8:
        return None
    xs = {left, right} | {p[0] for p in a + b if left < p[0] < right}
    values = []
    for x in xs:
        aa, bb = bounds_at(a, x), bounds_at(b, x)
        if aa and bb:
            values.append(bb[0] - aa[1] if above else bb[1] - aa[0])
    return (min(values) if above else max(values)) if values else None


def silhouette(obj, s, angle=0, shift=0):
    cx = obj["shed_length"] / 2
    cy = obj["shed_width"] / 2
    cosine, sine = math.cos(angle), math.sin(angle)
    wall = obj["shed_wall"]
    mat = obj.matrix_basis
    points = []
    for v in obj.data.vertices:
        p = v.co.copy()
        x, y = p.x - cx, p.y - cy
        p.x = cx + x * cosine - y * sine
        p.y = cy + x * sine + y * cosine + shift
        p = mat @ p
        u = p.x + s.width / 2 if wall in ("Front", "Rear") else p.y + s.length / 2
        points.append((u, p.z - s.floor_z))
    return hull(points)


def fit(ctx, s, retained=()):
    if s.crooked <= 0:
        return
    generated = [o for o in ctx.objects if o.get("shed_wall") and o.get("shed_plank")]
    fixed = {
        o["shed_key"]: o
        for o in retained
        if o.get("shed_wall") and o.get("shed_plan_bounds")
    }
    movable = [o for o in generated if o["shed_key"] not in fixed]
    boards = movable + list(fixed.values())
    silhouettes = {o: silhouette(o, s) for o in boards}
    for obj in sorted(movable, key=lambda o: o["shed_key"]):
        a, b, low, high = obj["shed_plan_bounds"]
        wall = obj["shed_wall"]
        roof_height, slope, ridge = obj["shed_roof_limit"]
        neighbors = [
            other for other in boards if other != obj and other["shed_wall"] == wall
        ]
        obstacles = list(obj["shed_openings"])

        def interval(angle):
            poly = silhouette(obj, s, angle)
            if min(p[0] for p in poly) < a - 1e-7 or max(p[0] for p in poly) > b + 1e-7:
                return None
            bottom = max(-p[1] for p in poly)
            top = min(
                (
                    min(roof_height, ridge - slope * abs(p[0] - s.width / 2))
                    if slope
                    else roof_height
                )
                - p[1]
                for p in poly
            )
            bottom = max(bottom, -s.plank_width / 2)
            top = min(top, s.plank_width / 2)
            for other in neighbors:
                _, _, olow, ohigh = other["shed_plan_bounds"]
                if olow >= high - 1e-6:
                    gap = clearance(poly, silhouettes[other], True)
                    if gap is not None:
                        top = min(top, gap - EPS)
                elif ohigh <= low + 1e-6:
                    gap = clearance(poly, silhouettes[other], False)
                    if gap is not None:
                        bottom = max(bottom, gap + EPS)
                # Same-level pieces are separated by their fixed horizontal fit bounds.
            for i in range(0, len(obstacles), 4):
                x0, x1, z0, z1 = obstacles[i : i + 4]
                rect = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
                if z0 >= high - 1e-6:
                    gap = clearance(poly, rect, True)
                    if gap is not None:
                        top = min(top, gap - EPS)
                elif z1 <= low + 1e-6:
                    gap = clearance(poly, rect, False)
                    if gap is not None:
                        bottom = max(bottom, gap + EPS)
            return (bottom, top) if bottom <= top + 1e-9 else None

        direction = rng_for(s.seed, obj["shed_key"] + ".crooked").choice((-1, 1))
        if interval(0) is None:
            obj["shed_crooked_angle"] = 0.0
            continue
        lo, hi = 0, math.radians(12)
        for _ in range(24):
            mid = (lo + hi) / 2
            if interval(mid * direction) is None:
                hi = mid
            else:
                lo = mid
        angle = lo * direction * s.crooked
        limits = interval(angle)
        if limits is None or abs(angle) < 1e-7:
            obj["shed_crooked_angle"] = 0.0
            continue
        shift = max(limits[0], min(0, limits[1]))
        cx, cy = obj["shed_length"] / 2, obj["shed_width"] / 2
        cosine, sine = math.cos(angle), math.sin(angle)
        for v in obj.data.vertices:
            x, y = v.co.x - cx, v.co.y - cy
            v.co.x = cx + x * cosine - y * sine
            v.co.y = cy + x * sine + y * cosine + shift
        obj.data.update()
        obj["shed_crooked_angle"] = math.degrees(angle)
        obj["shed_crooked_shift"] = shift
        silhouettes[obj] = silhouette(obj, s)
