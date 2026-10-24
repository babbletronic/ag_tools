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
options = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
settings = presets.dilapidated()
if "v11" in options:
    settings.crooked = 0.9
    settings.gap_randomizer = 1
    settings.gap_weight = 0.7
    settings.broken = 0.12
    settings.broken_max_percent = 45
prefix = "v11_" if "v11" in options else ""
root = generator.generate(settings)
bpy.context.scene.old_shed_root = root
camera = rig()
scene = bpy.context.scene
scene.cycles.samples = 64
scene.render.resolution_x = 1000
scene.render.resolution_y = 800
visibility.save_profile(root, "Exterior", camera)
(ROOT / "artifacts").mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(
    filepath=str(ROOT / "artifacts" / (prefix + "small_dilapidated.blend"))
)
render = "--" in sys.argv and "render" in sys.argv[sys.argv.index("--") + 1 :]
if render:
    scene.render.filepath = str(ROOT / "artifacts" / (prefix + "exterior.png"))
    bpy.ops.render.render(write_still=True)
visibility.set_part(root, "front", False, False)
visibility.set_part(root, "right", False, False)
visibility.set_part(root, "roof_covering", False, False)
visibility.save_profile(root, "Cutaway")
bpy.ops.wm.save_as_mainfile(
    filepath=str(ROOT / "artifacts" / (prefix + "cutaway.blend"))
)
if render:
    scene.render.filepath = str(ROOT / "artifacts" / (prefix + "cutaway.png"))
    bpy.ops.render.render(write_still=True)
