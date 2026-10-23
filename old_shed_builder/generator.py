"""Owned, transactional generation and explicit selective update boundaries."""

import hashlib
import json
import math
import uuid
from types import SimpleNamespace
import bpy
from .model import Settings, WALLS, validate
from .geometry import collection
from . import (
    foundation,
    framing,
    floor,
    roof,
    cladding,
    openings,
    wood,
    materials,
    visibility,
)

MATERIAL_FIELDS = {"aging", "roughness", "grain", "dirt", "water", "color_variation"}
FRAMING_FIELDS = {"header_depth", "collar_ties"}
CLADDING_FIELDS = {
    "leakage",
    "leak_gap",
    "leak_variation",
    "large_gaps",
    "missing",
    "leak_loose",
    "leak_separation",
    "leak_seed",
    "dramatic",
    "walls",
}


def fingerprint(obj):
    h = hashlib.sha256()
    h.update(repr(tuple(tuple(row) for row in obj.matrix_basis)).encode())
    h.update(repr(tuple(tuple(row) for row in obj.matrix_parent_inverse)).encode())
    h.update(str(obj.parent.get("shed_key", "root") if obj.parent else "").encode())
    h.update(repr((obj.hide_render, obj.hide_viewport, tuple(obj.color))).encode())
    h.update(
        repr(
            sorted((k, str(obj[k])) for k in obj.keys() if not k.startswith("shed_"))
        ).encode()
    )
    if obj.type == "MESH":
        for v in obj.data.vertices:
            h.update(repr(tuple(v.co)).encode())
        for p in obj.data.polygons:
            h.update(repr((tuple(p.vertices), p.material_index, p.use_smooth)).encode())
        h.update(
            repr(
                [
                    (m.name, materials.fingerprint(m)) if m else ""
                    for m in obj.data.materials
                ]
            ).encode()
        )
        for layer in obj.data.uv_layers:
            h.update(
                repr((layer.name, [tuple(loop.uv) for loop in layer.data])).encode()
            )
        if obj.data.shape_keys:
            for block in obj.data.shape_keys.key_blocks:
                h.update(
                    repr(
                        (block.name, block.value, [tuple(v.co) for v in block.data])
                    ).encode()
                )
    for mod in obj.modifiers:
        props = []
        for p in mod.bl_rna.properties:
            if p.identifier in ("rna_type", "name") or p.type not in (
                "BOOLEAN",
                "INT",
                "FLOAT",
                "STRING",
                "ENUM",
            ):
                continue
            try:
                value = getattr(mod, p.identifier)
                props.append((p.identifier, tuple(value) if p.is_array else value))
            except (AttributeError, TypeError):
                pass
        h.update(repr((mod.type, props)).encode())
    return h.hexdigest()


def is_edited(obj):
    """Animation and constraints are authored data, never generator defaults."""
    return bool(
        obj.get("shed_preserve")
        or obj.animation_data is not None
        or len(obj.constraints)
        or len(obj.vertex_groups)
        or fingerprint(obj) != obj.get("shed_signature")
    )


def owned(root):
    return [
        o
        for o in bpy.data.objects
        if o != root and o.get("shed_owner") == root["shed_owner"]
    ]


def discard(obj):
    data = obj.data if obj.type == "MESH" else None
    bpy.data.objects.remove(obj, do_unlink=True)
    if data and data.users == 0:
        bpy.data.meshes.remove(data)


def remove_tree(c):
    for child in list(c.children):
        remove_tree(child)
    bpy.data.collections.remove(c)


def check_scope(root, s, scope):
    if scope == "ALL":
        return
    if not root:
        raise ValueError("Generate a complete shed before selective updates")
    previous = json.loads(root["shed_settings"])
    current = s.to_dict()

    def equivalent(a, b):
        if isinstance(a, dict) and isinstance(b, dict):
            return a.keys() == b.keys() and all(equivalent(a[k], b[k]) for k in a)
        if isinstance(a, (float, int)) and isinstance(b, (float, int)):
            return math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-7)
        return a == b

    changed = {k for k in current if not equivalent(previous.get(k), current[k])} - {
        "preserve_edits"
    }
    allowed = (
        MATERIAL_FIELDS
        if scope == "MATERIALS"
        else CLADDING_FIELDS if scope == "CLADDING" else FRAMING_FIELDS
    )
    if changed - allowed:
        raise ValueError(
            "These parameter changes need Rebuild All: "
            + ", ".join(sorted(changed - allowed))
        )


def generate(s=None, stage=10, root=None, scope="ALL"):
    s = s or Settings()
    validate(s)
    if scope not in ("ALL", "FRAMING", "CLADDING", "MATERIALS"):
        raise ValueError("Unknown update scope")
    check_scope(root, s, scope)
    if root and scope == "MATERIALS":
        objects = owned(root)
        if s.preserve_edits:
            objects = [o for o in objects if not is_edited(o)]
        ctx = SimpleNamespace(root=root, owner=root["shed_owner"])
        materials.assign(ctx, s, objects)
        for obj in objects:
            obj["shed_signature"] = fingerprint(obj)
        root["shed_settings"] = json.dumps(s.to_dict(), sort_keys=True)
        cleanup_materials(ctx.owner)
        return root
    owner = root["shed_owner"] if root else uuid.uuid4().hex[:12]
    old_objects = owned(root) if root else []
    old_cols = (
        {
            c.get("shed_tag"): c
            for c in bpy.data.collections
            if c.get("shed_owner") == owner
        }
        if root
        else {}
    )
    staging = collection(
        bpy.context.scene.collection, "Old Shed " + owner, owner, "Root"
    )
    staging.hide_render = True
    staging.hide_viewport = True
    created_root = root is None
    if created_root:
        root = bpy.data.objects.new("Old Shed Controls", None)
        staging.objects.link(root)
        root["shed_owner"] = owner
        root["shed_root"] = True
        root.empty_display_type = "CUBE"
        root.empty_display_size = 0.2
    cols = {
        k: collection(staging, k, owner, k) for k in ("Foundation", "Floor", "Roof")
    }
    for wall in WALLS:
        wc = collection(staging, wall, owner, wall)
        for part in ("Framing", "Cladding", "Fixtures"):
            key = wall + "." + part
            cols[key] = collection(wc, part, owner, key)
    for part in ("Framing", "Covering"):
        key = "Roof." + part
        cols[key] = collection(cols["Roof"], part, owner, key)
    ctx = SimpleNamespace(
        root=root,
        owner=owner,
        collections=cols,
        component="framing",
        stage=stage,
        objects=[],
    )
    try:
        foundation.build(ctx, s)
        framing.build(ctx, s)
        if stage >= 2:
            floor.build(ctx, s)
            roof.build(ctx, s)
        if stage >= 3:
            ctx.component = "cladding"
            cladding.build(ctx, s)
        if stage >= 4:
            ctx.component = "fixtures"
            openings.build(ctx, s)
        if stage >= 5:
            wood.deform_all(ctx, s)
        if stage >= 6:
            materials.assign(ctx, s, ctx.objects)
    except Exception:
        for obj in reversed(ctx.objects):
            discard(obj)
        if created_root:
            bpy.data.objects.remove(root, do_unlink=True)
        remove_tree(staging)
        cleanup_materials(owner)
        raise
    targets = (
        {"framing"}
        if scope == "FRAMING"
        else {"cladding"} if scope == "CLADDING" else None
    )
    old_by_key = {o["shed_key"]: o for o in old_objects if o.get("shed_key")}
    preserved = set()
    if s.preserve_edits:
        for o in old_objects:
            if is_edited(o):
                preserved.add(o["shed_key"])
        # A hinged assembly is one editing unit; preserve its parent and siblings.
        if any(
            o.get("shed_component") == "fixtures" and o["shed_key"] in preserved
            for o in old_objects
        ):
            preserved.update(
                o["shed_key"]
                for o in old_objects
                if o.get("shed_component") == "fixtures"
            )
    accepted = []
    for obj in ctx.objects:
        key = obj["shed_key"]
        component = obj["shed_component"]
        if key in preserved or (targets is not None and component not in targets):
            continue
        accepted.append(obj)
    accepted_set = set(accepted)
    # Capture user collection links before replacing owned objects.
    extra_links = {
        key: [c for c in o.users_collection if c.get("shed_owner") != owner]
        for key, o in old_by_key.items()
    }
    for obj in old_objects:
        if obj["shed_key"] in preserved or (
            targets is not None and obj["shed_component"] not in targets
        ):
            continue
        discard(obj)
    for obj in reversed(ctx.objects):
        if obj not in accepted_set:
            discard(obj)
    for obj in accepted:
        for c in list(obj.users_collection):
            tag = c.get("shed_tag")
            if tag in old_cols:
                old_cols[tag].objects.link(obj)
                c.objects.unlink(obj)
        for c in extra_links.get(obj["shed_key"], []):
            if obj.name not in c.objects:
                c.objects.link(obj)
        obj.name = f'{owner} | {obj["shed_key"]}'
        obj["shed_signature"] = fingerprint(obj)
    if not created_root:
        remove_tree(staging)
    else:
        staging.hide_viewport = False
        staging.hide_render = False
    root["shed_settings"] = json.dumps(s.to_dict(), sort_keys=True)
    root["shed_stage"] = stage
    root["shed_preserved_count"] = len(preserved)
    if stage >= 7:
        visibility.apply(root)
    cleanup_materials(owner)
    return root


def cleanup_materials(owner):
    for mat in list(bpy.data.materials):
        if mat.get("shed_owner") == owner and mat.users == 0:
            bpy.data.materials.remove(mat)


def bake(root):
    """Independent evaluated mesh snapshot, initially hidden to prevent doubling."""
    bpy.context.view_layer.update()
    c = bpy.data.collections.new("Baked Old Shed (enable to display)")
    bpy.context.scene.collection.children.link(c)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    copied_materials = {}
    for obj in owned(root):
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
        clone = bpy.data.objects.new("Baked " + obj["shed_key"], mesh)
        c.objects.link(clone)
        clone.matrix_world = obj.matrix_world.copy()
        for i, mat in enumerate(mesh.materials):
            if mat not in copied_materials:
                copied = mat.copy()
                for key in list(copied.keys()):
                    del copied[key]
                # Freeze object-space weathering coordinates with a private Empty.
                if copied.use_nodes:
                    for node in copied.node_tree.nodes:
                        if node.type == "TEX_COORD" and node.object == root:
                            anchor = bpy.data.objects.get(c.name + " coordinates")
                            if anchor is None:
                                anchor = bpy.data.objects.new(
                                    c.name + " coordinates", None
                                )
                                c.objects.link(anchor)
                                anchor.matrix_world = root.matrix_world.copy()
                            node.object = anchor
                copied_materials[mat] = copied
            mesh.materials[i] = copied_materials[mat]
        clone.hide_render = obj.hide_render or any(
            col.hide_render for col in obj.users_collection
        )
    c.hide_render = True
    c.hide_viewport = True
    return c
