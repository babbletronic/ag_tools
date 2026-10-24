"""Solid subdivided planks. Local X=length, Y=width, Z=thickness."""

import math
import bpy
from mathutils import Matrix, Vector
from .geometry import mesh_object


def board(
    ctx, key, length, width, thickness, collection, origin, u, v, top=None, **kwargs
):
    nx = max(8, math.ceil(length / 0.14))
    ny = 6
    xs = [length * i / nx for i in range(nx + 1)]
    if top is not None:
        candidates = sorted(set(xs + list(kwargs.get("breaks", []))))
        xs = [candidates[0]]
        for x in candidates[1:]:
            if x - xs[-1] > 1e-6:
                xs.append(x)
        nx = len(xs) - 1
    vertices = []
    for side in (-1, 1):
        for x in xs:
            height = max(0.0001, top(x) if top else width)
            for j in range(ny + 1):
                vertices.append((x, height * j / ny, side * thickness / 2))
    layer = (nx + 1) * (ny + 1)

    def idx(i, j):
        return i * (ny + 1) + j

    faces = []
    face_labels = []
    for i in range(nx):
        for j in range(ny):
            a = idx(i, j)
            b = idx(i + 1, j)
            c = idx(i + 1, j + 1)
            d = idx(i, j + 1)
            faces.extend([(d, c, b, a), (a + layer, b + layer, c + layer, d + layer)])
            face_labels.extend((2, 0))
    boundary = [idx(i, 0) for i in range(nx + 1)]
    boundary += [idx(nx, j) for j in range(1, ny + 1)]
    boundary += [idx(i, ny) for i in range(nx - 1, -1, -1)]
    boundary += [idx(0, j) for j in range(ny - 1, 0, -1)]
    for a, b in zip(boundary, boundary[1:] + boundary[:1]):
        faces.append((a, b, b + layer, a + layer))
        ia, ja = divmod(a, ny + 1)
        ib, jb = divmod(b, ny + 1)
        face_labels.append(
            3 if ja == jb == 0 else 1 if ja == jb == ny else 4 if ia == ib == 0 else 5
        )
    obj = mesh_object(ctx, key, vertices, faces, collection)
    u = Vector(u)
    v = Vector(v)
    obj.location = origin
    obj.rotation_euler = Matrix((u, v, u.cross(v))).transposed().to_euler()
    obj["shed_plank"] = True
    labels = obj.data.attributes.new("shed_uv_face", "INT", "FACE")
    for item, value in zip(labels.data, face_labels):
        item.value = value
    obj["shed_length"] = length
    obj["shed_width"] = width
    obj["shed_thickness"] = thickness
    return obj


def rng_for(seed, key):
    import hashlib, random

    digest = hashlib.blake2b(f"{seed}:{key}".encode(), digest_size=8).digest()
    return random.Random(int.from_bytes(digest, "big"))


def deform(obj, s, attachments=None, loose=False, separation=None):
    """Smooth center-surface deformation; both skins receive identical offsets.

    Fasteners constrain full-width sections. Broken ends and V-shaped end splits
    are geometric cuts. Amplitudes are bounded relative to board dimensions;
    missing boards are handled by the siding layout, not by hidden geometry.
    """
    rng = rng_for(s.seed, obj["shed_key"])
    length = obj["shed_length"]
    width = obj["shed_width"]
    thick = obj["shed_thickness"]
    strength = s.variation
    phase = rng.uniform(-math.pi, math.pi)
    bow = min(s.bow, thick * 0.65) * strength * rng.uniform(-1, 1)
    twist = math.radians(min(s.twist, 12)) * strength * rng.uniform(-1, 1)
    cup = min(s.cup, thick * 0.35) * strength * rng.uniform(-1, 1)
    edge = min(s.edge, width * 0.025) * strength
    split = min(s.split, length * 0.14) * strength * rng.random()
    damage_rng = rng_for(s.seed, obj["shed_key"] + ".breaks")
    damaged = damage_rng.random() < s.broken * strength and s.broken_max_percent > 0
    mode = damage_rng.choice(("START", "END", "BOTH")) if damaged else "NONE"
    total_cut = (
        (length * s.broken_max_percent / 100 * strength * damage_rng.uniform(0.15, 1))
        if damaged
        else 0
    )
    start_share = (
        damage_rng.uniform(0.25, 0.75)
        if mode == "BOTH"
        else (1 if mode == "START" else 0)
    )
    start_cut, end_cut = total_cut * start_share, total_cut * (1 - start_share)
    # Keep the V split monotone even when a board is almost completely broken off.
    split = min(split, (length - total_cut) * 0.10)
    obj["shed_break_mode"] = mode
    obj["shed_break_start"] = start_cut
    obj["shed_break_end"] = end_cut
    detached = loose or rng.random() < s.loose * strength
    separation = min(0.15, separation if separation is not None else s.separation) * (
        1 if loose else strength
    )
    points = sorted(
        set([max(0, min(length, x)) for x in (attachments or [0.06, length - 0.06])])
    )
    if not points:
        points = [0, length]
    obj["shed_attachment_positions"] = points
    obj["shed_detached"] = detached
    obj["shed_broken"] = damaged
    for vertex in obj.data.vertices:
        x, y, z = vertex.co
        t = x / max(length, 1e-6)
        q = y / max(width, 1e-6)
        left = start_cut * (0.8 + 0.2 * math.cos(q * math.pi * 4 + phase))
        right = end_cut * (0.8 + 0.2 * math.sin(q * math.pi * 4 - phase))
        # A monotone remap leaves a positive solid even at the 95% damage limit.
        x = left + (length - left - right) * t
        original_x = x
        t = x / max(length, 1e-6)
        # Smooth envelope is exactly zero at supported cross-sections.
        if x < points[0]:
            envelope = min(1, (points[0] - x) / 0.12) ** 2
        elif x > points[-1]:
            envelope = min(1, (x - points[-1]) / 0.12) ** 2
        else:
            envelope = 0
            for a, b in zip(points, points[1:]):
                if a <= x <= b and b - a > 1e-8:
                    envelope = math.sin(math.pi * (x - a) / (b - a)) ** 2
                    break
        angle = twist * envelope * math.sin(math.pi * t + phase)
        yc = y - width / 2
        # Surface-normal thickness follows twist: no zero-thickness fake displacement.
        ry = yc * math.cos(angle) - z * math.sin(angle)
        rz = yc * math.sin(angle) + z * math.cos(angle)
        offset = bow * envelope + cup * (2 * q - 1) ** 2 * envelope
        if detached:
            last_fixed = points[-2] if len(points) > 1 else points[0]
            free = max(0, (original_x - last_fixed) / max(length - last_fixed, 0.001))
            offset += separation * free**2
        # End boundary indents at the center, leaving a real V-shaped split.
        notch = max(0, 1 - abs(q - 0.5) * 6)
        x += split * notch * (1 - t) ** 6
        y = width / 2 + ry + edge * math.sin(original_x * 3.1 + phase) * (2 * q - 1)
        vertex.co = (x, y, rz + offset)
    obj.data.update()


def deform_all(ctx, s):
    for obj in ctx.objects if hasattr(ctx, "objects") else list(bpy.data.objects):
        if obj.get("shed_owner") != ctx.owner or not obj.get("shed_plank"):
            continue
        if ".siding." in obj["shed_key"]:
            length = obj["shed_length"]
            count = max(1, math.ceil(length / s.stud_spacing))
            points = (
                [min(0.035, length * 0.1)]
                + [length * i / count for i in range(1, count)]
                + [length - min(0.035, length * 0.1)]
            )
        elif obj["shed_key"].startswith("floor.board"):
            length = obj["shed_length"]
            n = math.ceil((length - s.stud_width) / s.joist_spacing)
            points = [
                s.stud_width / 2 + (length - s.stud_width) * i / n for i in range(n + 1)
            ]
        else:
            points = None
        if obj.get("shed_supports") is not None:
            points = list(obj["shed_supports"])
        deform(
            obj,
            s,
            points,
            loose=obj.get("shed_leak_loose", False),
            separation=max(s.separation, obj.get("shed_leak_separation", 0)),
        )
