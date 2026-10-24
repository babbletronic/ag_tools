"""Connected timber nets and deterministic, material-group 0–1 atlases.

Net layout (U is timber length), matching the supplied reference:
             bottom
             back
             top
       left  front  right

Simple solids use one connected island. Rafter notches and other non-box cuts
use additional small islands beneath that net when a rectangular fold cannot
represent them without overlap. Physical dimensions are retained until packing.
"""

import math
from mathutils import Vector

FRONT, TOP, BACK, BOTTOM, LEFT, RIGHT = range(6)
PADDING = 0.001


def group_for(obj):
    key = obj["shed_key"]
    kind = obj.get("shed_material", "Wood")
    if kind == "Glass":
        return "Glass." + key.split(".shard.")[0]
    if kind != "Wood":
        return kind
    if ".siding." in key:
        return "Cladding"
    if key.startswith("roof.sheathing."):
        return "RoofSheathing"
    if key.startswith("roof.cover."):
        return "RoofCovering"
    if key.startswith("floor.board."):
        return "Floorboards"
    if obj.get("shed_component") == "fixtures":
        return "DoorsWindows"
    return "Framing"


def axes_for(obj):
    if obj.get("shed_plank"):
        return Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
    if obj.get("shed_uv_primitive") == "PRISM":
        edges = [
            obj.data.vertices[e.vertices[1]].co - obj.data.vertices[e.vertices[0]].co
            for e in obj.data.edges
        ]
        candidates = [v for v in edges if abs(v.y) < 1e-6]
        u = max(candidates, key=lambda v: v.length_squared).normalized()
        if u.x < 0:
            u = -u
        n = Vector((0, -1, 0))
        return u, n.cross(u), n
    extents = [
        max(v.co[i] for v in obj.data.vertices)
        - min(v.co[i] for v in obj.data.vertices)
        for i in range(3)
    ]
    order = sorted(range(3), key=lambda i: (-extents[i], i))
    basis = [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]
    u, v = basis[order[0]], basis[order[1]]
    return u, v, u.cross(v)


def unwrap(obj):
    mesh = obj.data
    u, v, n = axes_for(obj)
    coordinates = [(p.co.dot(u), p.co.dot(v), p.co.dot(n)) for p in mesh.vertices]
    minimum = [min(p[i] for p in coordinates) for i in range(3)]
    coordinates = [tuple(p[i] - minimum[i] for i in range(3)) for p in coordinates]
    length, width, thickness = [max(p[i] for p in coordinates) for i in range(3)]
    if min(length, width, thickness) <= 1e-7:
        raise ValueError(f'Cannot unwrap a zero-thickness solid: {obj["shed_key"]}')
    attr = mesh.attributes.get("shed_uv_face")
    top_at = {}
    if obj.get("shed_plank"):
        for x, y, z in coordinates:
            top_at[x] = max(top_at.get(x, 0), y)
    layer = mesh.uv_layers.get("UVMap") or mesh.uv_layers.new(name="UVMap")
    grain = mesh.uv_layers.get("WoodGrain") or mesh.uv_layers.new(name="WoodGrain")
    chart_width = length + 2 * thickness
    chart_height = 2 * width + 2 * thickness
    extra_y = chart_height + 0.003
    for polygon in mesh.polygons:
        points = [coordinates[i] for i in polygon.vertices]
        face = attr.data[polygon.index].value if attr else None
        if face is None:
            tests = (
                (2, thickness, FRONT),
                (1, width, TOP),
                (2, 0, BACK),
                (1, 0, BOTTOM),
                (0, 0, LEFT),
                (0, length, RIGHT),
            )
            face = next(
                (
                    label
                    for axis, value, label in tests
                    if all(abs(p[axis] - value) < 1e-6 for p in points)
                ),
                None,
            )
        if face is not None:
            values = []
            for x, y, z in points:
                w = top_at.get(x, width)
                if face == FRONT:
                    uv = (thickness + x, y)
                elif face == TOP:
                    uv = (thickness + x, w + thickness - z)
                elif face == BACK:
                    uv = (thickness + x, 2 * w + thickness - y)
                elif face == BOTTOM:
                    uv = (thickness + x, 2 * w + thickness + z)
                elif face == LEFT:
                    uv = (z, y)
                else:
                    uv = (thickness + length + thickness - z, y)
                values.append(uv)
        else:
            # Isolate irregular notch/cut faces; preserve area and avoid folded overlaps.
            verts = [mesh.vertices[i].co for i in polygon.vertices]
            edges = [b - a for a, b in zip(verts, verts[1:] + verts[:1])]
            uu = max(edges, key=lambda e: e.length_squared).normalized()
            vv = polygon.normal.cross(uu).normalized()
            projected = [(p.dot(uu), p.dot(vv)) for p in verts]
            xmin = min(p[0] for p in projected)
            ymin = min(p[1] for p in projected)
            values = [(x - xmin, y - ymin + extra_y) for x, y in projected]
            chart_width = max(chart_width, max(p[0] for p in values))
            extra_y = max(p[1] for p in values) + 0.003
            chart_height = extra_y
        for index, value in zip(polygon.loop_indices, values):
            layer.data[index].uv = value
            grain.data[index].uv = (
                value[0] / max(length, 0.01),
                value[1] / max(width, 0.01),
            )
    mesh.uv_layers.active_index = mesh.uv_layers.find("UVMap")
    layer.active_render = True
    obj["shed_uv_group"] = group_for(obj)
    obj["shed_uv_chart_size"] = (chart_width, chart_height)
    obj["shed_uv_layout_version"] = 1
    mark_seams(mesh, layer)


def mark_seams(mesh, layer):
    edges = {}
    for face in mesh.polygons:
        loops = list(face.loop_indices)
        for a, b in zip(loops, loops[1:] + loops[:1]):
            va, vb = mesh.loops[a].vertex_index, mesh.loops[b].vertex_index
            edge = tuple(sorted((va, vb)))
            coords = (tuple(layer.data[a].uv), tuple(layer.data[b].uv))
            if va > vb:
                coords = coords[::-1]
            edges.setdefault(edge, []).append(coords)
    for edge in mesh.edges:
        values = edges[tuple(sorted(edge.vertices))]
        edge.use_seam = len(values) != 2 or any(
            abs(values[0][i][j] - values[1][i][j]) > 1e-6
            for i in range(2)
            for j in range(2)
        )


def unwrap_objects(objects):
    for obj in objects:
        if obj.type == "MESH":
            unwrap(obj)


def intersect(a, b):
    return (
        a[0] < b[0] + b[2] - 1e-10
        and b[0] < a[0] + a[2] - 1e-10
        and a[1] < b[1] + b[3] - 1e-10
        and b[1] < a[1] + a[3] - 1e-10
    )


def subtract_rect(free, used):
    result = []
    ux, uy, uw, uh = used
    for rect in free:
        x, y, w, h = rect
        if not intersect(rect, used):
            result.append(rect)
            continue
        if ux > x:
            result.append((x, y, ux - x, h))
        if ux + uw < x + w:
            result.append((ux + uw, y, x + w - ux - uw, h))
        if uy > y:
            result.append((x, y, w, uy - y))
        if uy + uh < y + h:
            result.append((x, uy + uh, w, y + h - uy - uh))
    result = list(dict.fromkeys(r for r in result if r[2] > 1e-8 and r[3] > 1e-8))
    return [
        r
        for i, r in enumerate(result)
        if not any(
            i != j
            and r[0] >= q[0] - 1e-10
            and r[1] >= q[1] - 1e-10
            and r[0] + r[2] <= q[0] + q[2] + 1e-10
            and r[1] + r[3] <= q[1] + q[3] + 1e-10
            for j, q in enumerate(result)
        )
    ]


def occupied_rect(obj):
    layer = obj.data.uv_layers.get("UVMap")
    if not layer:
        return None
    xs = [v.uv.x for v in layer.data]
    ys = [v.uv.y for v in layer.data]
    x, y = max(0, min(xs) - PADDING), max(0, min(ys) - PADDING)
    return x, y, min(1, max(xs) + PADDING) - x, min(1, max(ys) + PADDING) - y


def pack_objects(objects, retained=()):
    groups = {}
    for obj in objects:
        if obj.type == "MESH":
            groups.setdefault(obj["shed_uv_group"], []).append(obj)
    for group, members in sorted(groups.items()):
        free = [(0.0, 0.0, 1.0, 1.0)]
        for obj in retained:
            if obj.type == "MESH" and obj.get("shed_uv_group") == group:
                rect = occupied_rect(obj)
                if rect:
                    free = subtract_rect(free, rect)
        members = sorted(
            members,
            key=lambda o: (
                -o["shed_uv_chart_size"][1],
                -o["shed_uv_chart_size"][0],
                o["shed_key"],
            ),
        )

        def trial(scale):
            remaining = list(free)
            placements = {}
            for obj in members:
                w, h = obj["shed_uv_chart_size"]
                w = w * scale + 2 * PADDING
                h = h * scale + 2 * PADDING
                options = [r for r in remaining if r[2] >= w and r[3] >= h]
                if not options:
                    return None
                r = min(
                    options,
                    key=lambda r: (
                        min(r[2] - w, r[3] - h),
                        max(r[2] - w, r[3] - h),
                        r[1],
                        r[0],
                    ),
                )
                placements[obj] = (
                    r[0] + PADDING,
                    r[1] + PADDING,
                    w - 2 * PADDING,
                    h - 2 * PADDING,
                )
                remaining = subtract_rect(remaining, (r[0], r[1], w, h))
            return placements

        low = 0.0
        high = min(
            (1 - 2 * PADDING) / max(o["shed_uv_chart_size"][i] for o in members)
            for i in range(2)
        )
        best = None
        for _ in range(20):
            scale = (low + high) / 2
            result = trial(scale)
            if result is None:
                high = scale
            else:
                low = scale
                best = result
        if best is None or low < 1e-6:
            raise ValueError(
                f"No UV atlas space remains in {group}. Preserved UVs occupy the tile; disable Preserve User Edits or use a new shed."
            )
        for obj, (x, y, w, h) in best.items():
            for loop in obj.data.uv_layers["UVMap"].data:
                loop.uv = (x + loop.uv.x * low, y + loop.uv.y * low)
            obj["shed_uv_rect"] = (x, y, w, h)
            obj["shed_uv_scale"] = low
