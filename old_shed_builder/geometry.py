"""Mesh primitives with explicit outward winding and stable ownership metadata."""

import bpy
from mathutils import Vector

FACES = [
    (0, 3, 2, 1),
    (4, 5, 6, 7),
    (0, 1, 5, 4),
    (1, 2, 6, 5),
    (2, 3, 7, 6),
    (3, 0, 4, 7),
]


def mesh_object(ctx, key, vertices, faces, collection, material="Wood"):
    mesh = bpy.data.meshes.new(key)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(key, mesh)
    collection.objects.link(obj)
    obj.parent = ctx.root
    obj["shed_owner"] = ctx.owner
    obj["shed_key"] = key
    component = ctx.component
    if key.startswith("floor.board"):
        component = "floor_covering"
    elif key.startswith(("roof.cover.", "roof.sheathing.")):
        component = "roof_covering"
    obj["shed_component"] = component
    if hasattr(ctx, "objects"):
        ctx.objects.append(obj)
    obj["shed_material"] = material
    return obj


def box(ctx, key, center, size, collection, material="Wood"):
    x, y, z = (v / 2 for v in size)
    vertices = [
        (-x, -y, -z),
        (x, -y, -z),
        (x, y, -z),
        (-x, y, -z),
        (-x, -y, z),
        (x, -y, z),
        (x, y, z),
        (-x, y, z),
    ]
    obj = mesh_object(ctx, key, vertices, FACES, collection, material)
    obj.location = center
    bevel = obj.modifiers.new("Soft physical edges", "BEVEL")
    bevel.width = min(0.0015, min(size) / 12)
    bevel.segments = 2
    return obj


def member(ctx, key, a, b, width, depth, collection):
    direction = Vector(b) - Vector(a)
    obj = box(
        ctx,
        key,
        (Vector(a) + Vector(b)) / 2,
        (direction.length, width, depth),
        collection,
    )
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("X", "Z")
    return obj


def collection(parent, name, owner, tag):
    result = bpy.data.collections.new(name)
    parent.children.link(result)
    result["shed_owner"] = owner
    result["shed_tag"] = tag
    return result


def prism(ctx, key, profile, depth, collection, material="Wood"):
    """Extrude an X/Z profile along Y, normalizing outward winding."""
    import bmesh

    n = len(profile)
    vertices = [(x, y, z) for y in (-depth / 2, depth / 2) for x, z in profile]
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    obj = mesh_object(ctx, key, vertices, faces, collection, material)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj["shed_uv_primitive"] = "PRISM"
    return obj
