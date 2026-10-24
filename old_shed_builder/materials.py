"""Opaque procedural timber: longitudinal grain, weathering and board variation."""

import bpy
import json
import math
from .uvs import group_for
from .wood import rng_for


def node(tree, kind, name, x, y):
    n = tree.nodes.new(kind)
    n.label = name
    n.location = (x, y)
    return n


def wood_material(ctx, s, axis=0):
    mat = bpy.data.materials.new(f"Old Shed {ctx.owner} • Timber {axis}")
    mat["shed_owner"] = ctx.owner
    mat["shed_kind"] = "Wood"
    mat.diffuse_color = (0.23, 0.19, 0.14, 1)
    mat.use_nodes = True
    t = mat.node_tree
    t.nodes.clear()
    link = t.links.new
    output = node(t, "ShaderNodeOutputMaterial", "Surface", 1000, 0)
    bsdf = node(t, "ShaderNodeBsdfPrincipled", "Weathered opaque wood", 760, 0)
    link(bsdf.outputs["BSDF"], output.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = s.roughness
    coord = node(
        t, "ShaderNodeTexCoord", "Local grain / building weathering", -1000, 100
    )
    coord.object = ctx.root
    scale = node(t, "ShaderNodeVectorMath", "Longitudinal fibers", -800, 200)
    scale.operation = "MULTIPLY"
    scales = [72, 72, 72]
    scales[axis] = 2.5
    scale.inputs[1].default_value = scales
    grain_uv = node(t, "ShaderNodeUVMap", "Local grain coordinates", -1000, 350)
    grain_uv.uv_map = "WoodGrain"
    link(grain_uv.outputs["UV"], scale.inputs[0])
    atlas_uv = node(
        t, "ShaderNodeUVMap", "UVMap — image painting / baking atlas", -1000, 550
    )
    atlas_uv.uv_map = "UVMap"
    noise = node(t, "ShaderNodeTexNoise", "Nonrepeating wood fibers", -600, 250)
    noise.inputs["Scale"].default_value = 2.0
    noise.inputs["Detail"].default_value = 4
    noise.inputs["Roughness"].default_value = 0.72
    link(scale.outputs["Vector"], noise.inputs["Vector"])
    ramp = node(t, "ShaderNodeValToRGB", "Gray / brown aging", -360, 260)
    brown = [(0.055, 0.025, 0.009, 1), (0.31, 0.17, 0.064, 1)]
    gray = [(0.075, 0.078, 0.07, 1), (0.39, 0.40, 0.35, 1)]
    for i, e in enumerate(ramp.color_ramp.elements):
        e.position = 0.22 if i == 0 else 0.78
        e.color = tuple(
            brown[i][j] * (1 - s.aging) + gray[i][j] * s.aging for j in range(4)
        )
    link(noise.outputs["Fac"], ramp.inputs[0])
    info = node(t, "ShaderNodeObjectInfo", "Deterministic color per board", -360, 40)
    random_scale = node(t, "ShaderNodeVectorMath", "Per-board grain offset", -800, 450)
    random_scale.operation = "MULTIPLY"
    random_scale.inputs[1].default_value = (113, 67, 97)
    link(info.outputs["Color"], random_scale.inputs[0])
    offset = node(t, "ShaderNodeVectorMath", "Unique fiber field", -600, 450)
    offset.operation = "ADD"
    link(scale.outputs["Vector"], offset.inputs[0])
    link(random_scale.outputs[0], offset.inputs[1])
    link(offset.outputs[0], noise.inputs["Vector"])
    variation = node(t, "ShaderNodeMixRGB", "Board color variation", -100, 220)
    variation.blend_type = "MULTIPLY"
    variation.inputs[0].default_value = s.color_variation
    link(ramp.outputs["Color"], variation.inputs[1])
    link(info.outputs["Color"], variation.inputs[2])
    water_scale = node(
        t, "ShaderNodeVectorMath", "Gravity-aligned water streaks", -800, -200
    )
    water_scale.operation = "MULTIPLY"
    water_scale.inputs[1].default_value = (7, 7, 0.25)
    link(coord.outputs["Object"], water_scale.inputs[0])
    stains = node(t, "ShaderNodeTexNoise", "Water tracks", -600, -200)
    stains.inputs["Scale"].default_value = 3
    stains.inputs["Detail"].default_value = 2
    link(water_scale.outputs["Vector"], stains.inputs["Vector"])
    water = node(t, "ShaderNodeMath", "Water staining amount", -350, -180)
    water.operation = "MULTIPLY"
    water.inputs[1].default_value = s.water * 0.65
    link(stains.outputs["Fac"], water.inputs[0])
    water_mix = node(t, "ShaderNodeMixRGB", "Water-darkened fibers", 130, 200)
    water_mix.blend_type = "MULTIPLY"
    water_mix.inputs[2].default_value = (0.24, 0.29, 0.24, 1)
    link(water.outputs[0], water_mix.inputs[0])
    link(variation.outputs[0], water_mix.inputs[1])
    xyz = node(t, "ShaderNodeSeparateXYZ", "Height above ground", -600, -420)
    link(coord.outputs["Object"], xyz.inputs[0])
    dirt = node(t, "ShaderNodeMapRange", "Dirt near the base", -350, -400)
    dirt.inputs["From Min"].default_value = s.floor_z
    dirt.inputs["From Max"].default_value = s.floor_z + 1.0
    dirt.inputs["To Min"].default_value = s.dirt
    dirt.inputs["To Max"].default_value = 0
    link(xyz.outputs["Z"], dirt.inputs["Value"])
    dirt_mix = node(t, "ShaderNodeMixRGB", "Accumulated dirt", 400, 180)
    dirt_mix.blend_type = "MULTIPLY"
    dirt_mix.inputs[2].default_value = (0.19, 0.12, 0.055, 1)
    link(dirt.outputs["Result"], dirt_mix.inputs[0])
    link(water_mix.outputs[0], dirt_mix.inputs[1])
    link(dirt_mix.outputs[0], bsdf.inputs["Base Color"])
    bump = node(
        t, "ShaderNodeBump", "Fine fiber relief (geometry supplies damage)", 400, -100
    )
    bump.inputs["Strength"].default_value = s.grain * 0.32
    bump.inputs["Distance"].default_value = 0.0012
    link(noise.outputs["Fac"], bump.inputs["Height"])
    link(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def simple(ctx, name, color, roughness, metallic=0, transmission=0):
    mat = bpy.data.materials.new(f"Old Shed {ctx.owner} • {name}")
    mat["shed_owner"] = ctx.owner
    mat["shed_kind"] = name
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    p = mat.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = roughness
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Transmission Weight"].default_value = transmission
    p.inputs["IOR"].default_value = 1.45
    return mat


def assign(ctx, s, objects=None, reuse=()):
    objects = list(objects if objects is not None else bpy.data.objects)
    members = [
        o for o in objects if o.type == "MESH" and o.get("shed_owner") == ctx.owner
    ]
    groups = {
        o.get("shed_uv_group", group_for(o)): o.get("shed_material", "Wood")
        for o in members
    }
    materials = {}
    previous = json.loads(ctx.root.get("shed_settings", "{}"))
    fields = ("aging", "roughness", "grain", "dirt", "water", "color_variation")
    same = all(
        math.isclose(
            previous.get(k, getattr(s, k)), getattr(s, k), abs_tol=1e-7, rel_tol=1e-6
        )
        for k in fields
    )
    if same:
        for obj in reuse:
            if obj.type != "MESH":
                continue
            for mat in obj.data.materials:
                if (
                    mat
                    and mat.get("shed_uv_group") in groups
                    and mat.get("shed_signature") == fingerprint(mat)
                ):
                    materials[mat["shed_uv_group"]] = mat
    for group, kind in sorted(groups.items()):
        if group in materials:
            continue
        if kind == "Wood":
            mat = wood_material(ctx, s)
        elif kind == "Metal":
            mat = simple(ctx, "Metal", (0.085, 0.052, 0.027), 0.62, 0.8)
        elif kind == "Glass":
            mat = simple(ctx, "Glass", (0.86, 0.94, 0.90), 0.09, transmission=1)
        else:
            mat = simple(ctx, "Concrete", (0.22, 0.21, 0.18), 0.94)
        mat.name = f"Old Shed {ctx.owner} • {group}"
        mat["shed_uv_group"] = group
        mat["shed_signature"] = fingerprint(mat)
        materials[group] = mat
    for obj in members:
        group = obj.get("shed_uv_group", group_for(obj))
        obj.data.materials.clear()
        obj.data.materials.append(materials[group])
        value = rng_for(s.seed, obj["shed_key"]).uniform(0.45, 1)
        obj.color = (value, value * 0.97, value * 0.91, 1)
    return list(materials.values())


def fingerprint(mat):
    """Detect edits to generated material graphs without relying on material names."""
    import hashlib

    values = [tuple(mat.diffuse_color), mat.use_nodes]
    if mat.use_nodes:
        for n in mat.node_tree.nodes:
            props = []
            for p in n.bl_rna.properties:
                if p.identifier in (
                    "rna_type",
                    "location",
                    "width",
                    "height",
                    "dimensions",
                    "select",
                ):
                    continue
                if p.type not in ("BOOLEAN", "INT", "FLOAT", "STRING", "ENUM"):
                    continue
                try:
                    v = getattr(n, p.identifier)
                    props.append((p.identifier, tuple(v) if p.is_array else v))
                except (AttributeError, TypeError):
                    pass
            sockets = []
            for socket in n.inputs:
                if hasattr(socket, "default_value"):
                    v = socket.default_value
                    if isinstance(v, (float, int, bool, str)):
                        sockets.append(v)
                    elif v is None:
                        sockets.append(None)
                    else:
                        try:
                            sockets.append(tuple(v))
                        except TypeError:
                            sockets.append(v.name)
            ramp = (
                [(e.position, tuple(e.color)) for e in n.color_ramp.elements]
                if hasattr(n, "color_ramp")
                else []
            )
            values.append((n.bl_idname, n.name, props, sockets, ramp))
        values.append(
            sorted(
                (
                    link.from_node.name,
                    link.from_socket.identifier,
                    link.to_node.name,
                    link.to_socket.identifier,
                )
                for link in mat.node_tree.links
            )
        )
    return hashlib.sha256(repr(values).encode()).hexdigest()
