"""Create shot-ready exterior/cutaway examples; pass -- render for PNGs too."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import bpy
import old_shed_builder
from old_shed_builder import generator, presets, visibility
from scene_support import rig

old_shed_builder.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
root = generator.generate(presets.dilapidated())
bpy.context.scene.old_shed_root = root
camera = rig()
scene = bpy.context.scene
scene.cycles.samples = 64
scene.render.resolution_x = 1000
scene.render.resolution_y = 800
visibility.save_profile(root, "Exterior", camera)
(ROOT / "artifacts").mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(
    filepath=str(ROOT / "artifacts" / "small_dilapidated.blend")
)
render = "--" in sys.argv and "render" in sys.argv[sys.argv.index("--") + 1 :]
if render:
    scene.render.filepath = str(ROOT / "artifacts" / "exterior.png")
    bpy.ops.render.render(write_still=True)
visibility.set_part(root, "front", False, False)
visibility.set_part(root, "right", False, False)
visibility.set_part(root, "roof_covering", False, False)
visibility.save_profile(root, "Cutaway")
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "artifacts" / "cutaway.blend"))
if render:
    scene.render.filepath = str(ROOT / "artifacts" / "cutaway.png")
    bpy.ops.render.render(write_still=True)
