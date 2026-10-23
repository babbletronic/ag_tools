"""blender --background --factory-startup --python tests/run_stage.py -- 1"""

import os, sys, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bpy
from old_shed_builder.model import Settings, validate
from old_shed_builder.generator import generate

stage = int(sys.argv[sys.argv.index("--") + 1]) if "--" in sys.argv else 1
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
if stage >= 9:
    import old_shed_builder

    old_shed_builder.register()
s = Settings()
root = generate(s, stage)
if stage >= 9:
    bpy.context.scene.old_shed_root = root
    from old_shed_builder import properties

    roundtrip = properties.from_rna(bpy.context.scene.old_shed_settings)
    assert abs(roundtrip.width - s.width) < 1e-6
    assert roundtrip.window_a.wall == "Left"
objects = [
    o
    for o in bpy.data.objects
    if o.get("shed_owner") == root["shed_owner"] and o.type == "MESH"
]
assert len(objects) > 70, len(objects)
keys = {o["shed_key"] for o in objects}
for wall in ("Front", "Rear", "Left", "Right"):
    assert wall + ".plate.top.0" in keys and wall + ".plate.top.1" in keys
for wall, name in [("Front", "door"), ("Left", "window_a"), ("Right", "window_b")]:
    for suffix in ("king.L", "king.R", "jack.L", "jack.R", "header"):
        assert f"{wall}.{name}.{suffix}" in keys
if stage >= 2:
    assert "roof.ridge" in keys and "floor.joist.001" in keys
    assert any("gable.stud" in k for k in keys)
if stage >= 3:
    siding = [o for o in objects if ".siding." in o.get("shed_key", "")]
    assert len(siding) > 60
    assert all(len(o.data.vertices) > 100 for o in siding)
if stage >= 4:
    assert any("door.leaf" in k for k in keys)
    assert any("glass" in k and "shard" in k for k in keys)
    pivot = next(o for o in bpy.data.objects if o.get("shed_key") == "Front.door.pivot")
    assert abs(pivot.rotation_euler.z + math.radians(s.door_angle)) < 1e-6
if stage >= 6:
    assert all(len(o.data.materials) == 1 for o in objects)
    assert all(o.data.materials[0].use_nodes for o in objects)
if stage >= 7:
    from old_shed_builder import visibility

    count = len(bpy.data.objects)
    visibility.save_profile(root, "Exterior")
    visibility.set_part(root, "front", viewport=False, render=False)
    front = next(
        c
        for c in bpy.data.collections
        if c.get("shed_owner") == root["shed_owner"] and c.get("shed_tag") == "Front"
    )
    assert front.hide_viewport and front.hide_render
    visibility.set_part(root, "roof_covering", viewport=False, render=True)
    covering = next(
        c
        for c in bpy.data.collections
        if c.get("shed_owner") == root["shed_owner"]
        and c.get("shed_tag") == "Roof.Covering"
    )
    assert covering.hide_viewport and not covering.hide_render
    visibility.restore_profile(root, "Exterior")
    assert not front.hide_render and not front.hide_viewport
    assert len(bpy.data.objects) == count
# Each solid is closed, with positive signed volume and no degenerate face.
import bmesh

for obj in objects:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(e.is_manifold for e in bm.edges), obj.name
    assert bm.calc_volume(signed=True) > 0, obj.name
    assert all(f.calc_area() > 1e-10 for f in bm.faces), obj.name
    bm.free()
bad = Settings()
bad.door.position = 0.1
try:
    validate(bad)
except ValueError:
    pass
else:
    raise AssertionError("Impossible opening accepted")
sys.path.insert(0, str(ROOT / "tests"))
from scene_support import rig

rig()
(ROOT / "artifacts").mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(
    filepath=str(ROOT / "artifacts" / f"stage_{stage:02}.blend")
)
print(f"STAGE {stage} PASS: {len(objects)} closed, outward-wound mesh objects")
