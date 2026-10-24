"""Individual plates, studs, load-bearing opening frames and corner backing."""

from .model import WALLS, wall_point, subtract
from .geometry import box


def build(ctx, s):
    sw, d, z0 = s.stud_width, s.stud_depth, s.floor_z
    for wall in WALLS:
        c = ctx.collections[wall + ".Framing"]
        span = s.span(wall)
        lo, hi = (0, span) if wall in ("Front", "Rear") else (d, span - d)

        def timber(key, a, b, z, h, depth=d):
            if b - a < 0.001 or h < 0.001:
                return
            size = (b - a, depth, h) if wall in ("Front", "Rear") else (depth, b - a, h)
            return box(
                ctx,
                f"{wall}.{key}",
                wall_point(s, wall, (a + b) / 2, z0 + z + h / 2),
                size,
                c,
            )

        door_cuts = [
            (o.position - o.width / 2, o.position + o.width / 2)
            for n, o in s.openings(wall)
            if n == "door"
        ]
        for i, (a, b) in enumerate(subtract((lo, hi), door_cuts)):
            timber(f"plate.bottom.{i}", a, b, 0, sw)
        for i in range(2):
            timber(f"plate.top.{i}", lo, hi, s.wall_height - (i + 1) * sw, sw)
        top = s.wall_height - 2 * sw
        occupied = []
        for name, o in s.openings(wall):
            a, b = o.position - o.width / 2, o.position + o.width / 2
            end = o.bottom + o.height
            header_height = s.header_height(name)
            for side, x in [("L", a - 1.5 * sw), ("R", b + 1.5 * sw)]:
                timber(f"{name}.king.{side}", x - sw / 2, x + sw / 2, sw, top - sw)
            for side, x in [("L", a - sw / 2), ("R", b + sw / 2)]:
                timber(f"{name}.jack.{side}", x - sw / 2, x + sw / 2, sw, end - sw)
            timber(f"{name}.header", a - sw, b + sw, end, header_height)
            if name != "door":
                timber(f"{name}.sill", a, b, o.bottom - sw, sw)
            occupied.append((a - 2 * sw, b + 2 * sw))
            x = a + sw / 2
            i = 0
            while x <= b - sw / 2 + 0.0001:
                timber(
                    f"{name}.cripple.upper.{i}",
                    x - sw / 2,
                    x + sw / 2,
                    end + header_height,
                    top - end - header_height,
                )
                if name != "door":
                    timber(
                        f"{name}.cripple.lower.{i}",
                        x - sw / 2,
                        x + sw / 2,
                        sw,
                        o.bottom - 2 * sw,
                    )
                x += s.stud_spacing
                i += 1
        positions = [lo + sw / 2, hi - sw / 2]
        if wall in ("Front", "Rear"):
            positions += [d - sw / 2, span - d + sw / 2]
        x = lo + s.stud_spacing
        while x < hi - sw:
            if all(abs(x - p) >= sw + 0.001 for p in positions):
                positions.append(x)
            x += s.stud_spacing
        for i, x in enumerate(sorted(positions)):
            if any(
                x + sw / 2 > a - 0.0001 and x - sw / 2 < b + 0.0001 for a, b in occupied
            ):
                continue
            timber(f"stud.{i:03}", x - sw / 2, x + sw / 2, sw, top - sw)
