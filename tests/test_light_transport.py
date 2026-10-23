"""Verify geometric apertures by ray tests AND actual Cycles illumination."""

import json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bpy
from mathutils import Vector
from old_shed_builder.model import Settings
from old_shed_builder.generator import generate

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
s = Settings()
s.door.enabled = False
s.window_a.enabled = False
s.window_b.enabled = False
s.variation = 0
s.plank_gap = 0
s.leakage = 0
s.preserve_edits = False
root = generate(s)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 32
scene.cycles.use_denoising = False
scene.render.resolution_x = 480
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "AgX"
world = bpy.data.worlds.new("Black world for isolated sunlight")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[1].default_value = 0
scene.world = world
sun_data = bpy.data.lights.new("Physical sunlight", "SUN")
sun_data.energy = 3
sun_data.angle = 0.015
sun = bpy.data.objects.new("Physical sunlight", sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(65), 0, 0)
camera = bpy.data.objects.new(
    "Interior leakage test", bpy.data.cameras.new("Interior test lens")
)
scene.collection.objects.link(camera)
camera.location = (1.05, -1.35, s.floor_z + 1.55)
camera.rotation_euler = (
    (Vector((-0.25, 1.2, s.floor_z + 0.7)) - camera.location)
    .to_track_quat("-Z", "Y")
    .to_euler()
)
camera.data.lens = 22
scene.camera = camera


def apertures():
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    rays = 0
    holes = 0
    for ix in range(49):
        x = -s.width / 2 + 0.15 + (s.width - 0.3) * (ix + 0.5) / 49
        for iz in range(97):
            z = s.floor_z + 0.12 + (s.wall_height - 0.25) * (iz + 0.5) / 97
            hit = scene.ray_cast(
                depsgraph,
                Vector((x, -s.length / 2 - 0.12, z)),
                Vector((0, 1, 0)),
                distance=0.4,
            )[0]
            rays += 1
            holes += not hit
    return {"rays": rays, "unblocked": holes}


def render(name):
    path = ROOT / "artifacts" / f"{name}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(str(path), check_existing=False)
    pixels = list(image.pixels)
    mean = sum(
        pixels[i] + pixels[i + 1] + pixels[i + 2] for i in range(0, len(pixels), 4)
    ) / (len(pixels) / 4 * 3)
    bpy.data.images.remove(image)
    return mean


ROOT.joinpath("artifacts").mkdir(exist_ok=True)
closed = apertures()
closed["mean_rgb"] = render("leakage_closed")
s.leakage = 1
s.leak_gap = 0.035
s.missing = 0
s.large_gaps = 0.1
root = generate(s, root=root, scope="CLADDING")
opened = apertures()
opened["mean_rgb"] = render("leakage_open")
assert closed["unblocked"] == 0, closed
assert opened["unblocked"] > closed["unblocked"] + 300, (closed, opened)
assert opened["mean_rgb"] > max(0.005, closed["mean_rgb"] * 1.5), (closed, opened)
result = {
    "closed": closed,
    "open": opened,
    "renderer": "Cycles CPU, 32 samples, no denoising",
    "pass": True,
}
(ROOT / "artifacts" / "light_transport.json").write_text(
    json.dumps(result, indent=2) + "\n"
)
bpy.ops.wm.save_as_mainfile(
    filepath=str(ROOT / "artifacts" / "light_leakage_test.blend")
)
print("LIGHT TRANSPORT PASS", json.dumps(result))
