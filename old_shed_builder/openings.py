"""Door leaf, hinges, jambs, glazed window frames and optional shutters."""

import math
import bpy
from mathutils import Vector
from .geometry import box, mesh_object
from .model import WALLS, wall_point
from .wood import board


def cylinder(ctx, key, center, radius, height, c):
    n = 16
    vertices = [
        (
            radius * math.cos(i * 2 * math.pi / n),
            radius * math.sin(i * 2 * math.pi / n),
            z,
        )
        for z in (-height / 2, height / 2)
        for i in range(n)
    ]
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    o = mesh_object(ctx, key, vertices, faces, c, "Metal")
    o.location = center
    return o


def build(ctx, s):
    for wall in WALLS:
        c = ctx.collections[wall + ".Fixtures"]
        span = s.span(wall)
        axis = (1, 0, 0) if wall in ("Front", "Rear") else (0, 1, 0)
        normal = {
            "Front": (0, -1, 0),
            "Rear": (0, 1, 0),
            "Left": (-1, 0, 0),
            "Right": (1, 0, 0),
        }[wall]
        reverse = wall in ("Rear", "Left")

        def timber(key, u, z, width, height, depth, out=0, material="Wood"):
            size = (
                (width, depth, height)
                if wall in ("Front", "Rear")
                else (depth, width, height)
            )
            return box(
                ctx,
                f"{wall}.{key}",
                wall_point(s, wall, u, s.floor_z + z, out),
                size,
                c,
                material,
            )

        for name, o in s.openings(wall):
            a, b = o.position - o.width / 2, o.position + o.width / 2
            base = o.bottom
            end = base + o.height
            depth = s.stud_depth + s.plank_thickness
            jamb = 0.028
            for side, x in [("L", a + jamb / 2), ("R", b - jamb / 2)]:
                timber(
                    f"{name}.jamb.{side}",
                    x,
                    base + o.height / 2,
                    jamb,
                    o.height,
                    depth,
                    s.plank_thickness / 2,
                )
            timber(
                f"{name}.jamb.top",
                o.position,
                end - jamb / 2,
                o.width - 2 * jamb,
                jamb,
                depth,
                s.plank_thickness / 2,
            )
            if name == "door":
                pivot = bpy.data.objects.new(f"{wall}.door.hinge_pivot", None)
                c.objects.link(pivot)
                pivot.parent = ctx.root
                pivot["shed_owner"] = ctx.owner
                pivot["shed_key"] = f"{wall}.door.pivot"
                pivot["shed_component"] = ctx.component
                if hasattr(ctx, "objects"):
                    ctx.objects.append(pivot)
                hinge = Vector(
                    wall_point(
                        s, wall, a + jamb + 0.004, s.floor_z + 0.012, depth / 2 + 0.015
                    )
                )
                pivot.location = hinge
                leaf = []
                clear = o.width - 2 * jamb - 0.008
                h = o.height - jamb - 0.018
                n = math.ceil(clear / s.plank_width)
                width = (clear - (n - 1) * 0.002) / n
                for i in range(n):
                    u = a + jamb + 0.004 + i * (width + 0.002)
                    # Board local length axis is vertical; width points along the wall.
                    v = tuple(-t for t in axis) if not reverse else axis
                    origin = wall_point(
                        s,
                        wall,
                        u + width if not reverse else u,
                        s.floor_z + 0.012,
                        depth / 2 + 0.015,
                    )
                    leaf.append(
                        board(
                            ctx,
                            f"{wall}.door.leaf.{i:02}",
                            h,
                            width,
                            0.032,
                            c,
                            origin,
                            (0, 0, 1),
                            v,
                        )
                    )
                for i, z in enumerate((0.24, h - 0.24)):
                    leaf.append(
                        timber(
                            f"door.batten.{i}",
                            a + jamb + 0.004 + clear / 2,
                            z,
                            clear - 0.04,
                            0.09,
                            0.026,
                            depth / 2 - 0.014,
                        )
                    )
                # Real diagonal brace on the inside face.
                from .geometry import member

                leaf.append(
                    member(
                        ctx,
                        f"{wall}.door.diagonal",
                        wall_point(
                            s,
                            wall,
                            a + jamb + 0.05,
                            s.floor_z + 0.30,
                            depth / 2 - 0.014,
                        ),
                        wall_point(
                            s,
                            wall,
                            b - jamb - 0.05,
                            s.floor_z + h - 0.30,
                            depth / 2 - 0.014,
                        ),
                        0.026,
                        0.075,
                        c,
                    )
                )
                for i, z in enumerate((0.28, h - 0.28)):
                    cylinder(
                        ctx,
                        f"{wall}.door.hinge.{i}",
                        wall_point(
                            s, wall, a + jamb + 0.004, s.floor_z + z, depth / 2 + 0.015
                        ),
                        0.012,
                        0.10,
                        c,
                    )
                    leaf.append(
                        timber(
                            f"door.hinge.strap.{i}",
                            a + jamb + 0.13,
                            z,
                            0.25,
                            0.035,
                            0.006,
                            depth / 2 + 0.034,
                            "Metal",
                        )
                    )
                leaf.append(
                    timber(
                        "door.handle",
                        b - jamb - 0.09,
                        h * 0.5,
                        0.025,
                        0.14,
                        0.025,
                        depth / 2 + 0.047,
                        "Metal",
                    )
                )
                for obj in leaf:
                    obj.parent = pivot
                    obj.location -= hinge
                direction = -1 if wall in ("Front", "Right") else 1
                pivot.rotation_euler.z = direction * math.radians(s.door_angle)
            else:
                timber(
                    f"{name}.jamb.sill",
                    o.position,
                    base + jamb / 2,
                    o.width - 2 * jamb,
                    jamb,
                    depth + 0.03,
                    s.plank_thickness / 2 + 0.015,
                )
                mid = base + o.height / 2
                out = s.stud_depth / 2 - 0.01
                timber(
                    f"{name}.mullion.vertical",
                    o.position,
                    mid,
                    0.025,
                    o.height - 2 * jamb,
                    0.035,
                    out,
                )
                timber(
                    f"{name}.mullion.horizontal",
                    o.position,
                    mid,
                    o.width - 2 * jamb,
                    0.025,
                    0.035,
                    out,
                )
                if s.glass:
                    for ix in range(2):
                        for iz in range(2):
                            left = a + jamb if ix == 0 else o.position + 0.0125
                            right = o.position - 0.0125 if ix == 0 else b - jamb
                            low = base + jamb if iz == 0 else mid + 0.0125
                            high = mid - 0.0125 if iz == 0 else end - jamb
                            # A broken pane retains two real triangular shards and a hole.
                            key = f"{wall}.{name}.glass.{ix}.{iz}"
                            if s.broken_glass and ix == 1 and iz == 1:
                                for j, tri in enumerate(
                                    [
                                        [
                                            (left, low),
                                            (right, low),
                                            (right, low + (high - low) * 0.3),
                                        ],
                                        [
                                            (left, high),
                                            (left, low + (high - low) * 0.65),
                                            (left + (right - left) * 0.35, high),
                                        ],
                                    ]
                                ):
                                    vertices = [
                                        wall_point(s, wall, x, s.floor_z + z, out + t)
                                        for t in (-0.002, 0.002)
                                        for x, z in tri
                                    ]
                                    obj = mesh_object(
                                        ctx,
                                        key + f".shard.{j}",
                                        vertices,
                                        [
                                            (0, 2, 1),
                                            (3, 4, 5),
                                            (0, 1, 4, 3),
                                            (1, 2, 5, 4),
                                            (2, 0, 3, 5),
                                        ],
                                        c,
                                        "Glass",
                                    )
                                    import bmesh

                                    bm = bmesh.new()
                                    bm.from_mesh(obj.data)
                                    bmesh.ops.recalc_face_normals(
                                        bm, faces=list(bm.faces)
                                    )
                                    bm.to_mesh(obj.data)
                                    bm.free()
                            else:
                                timber(
                                    f"{name}.glass.{ix}.{iz}",
                                    (left + right) / 2,
                                    (low + high) / 2,
                                    right - left,
                                    high - low,
                                    0.004,
                                    out,
                                    "Glass",
                                )
                if s.shutters:
                    for side in (-1, 1):
                        width = o.width / 2 - 0.03
                        n = 3
                        for i in range(n):
                            u = (
                                a - width - 0.04 if side < 0 else b + 0.04
                            ) + i * width / n
                            v = tuple(-t for t in axis) if not reverse else axis
                            origin = wall_point(
                                s,
                                wall,
                                u + width / n if not reverse else u,
                                s.floor_z + base,
                                depth / 2 + 0.03,
                            )
                            board(
                                ctx,
                                f"{wall}.{name}.shutter.{side}.{i}",
                                o.height,
                                width / n - 0.003,
                                0.022,
                                c,
                                origin,
                                (0, 0, 1),
                                v,
                            )
                        for j, z in enumerate((base + 0.1, end - 0.1)):
                            timber(
                                f"{name}.shutter.batten.{side}.{j}",
                                (
                                    a - width / 2 - 0.04
                                    if side < 0
                                    else b + width / 2 + 0.04
                                ),
                                z,
                                width,
                                0.06,
                                0.018,
                                depth / 2 + 0.05,
                            )
