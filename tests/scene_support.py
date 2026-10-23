"""Deterministic, non-add-on camera/light rig for sample and inspection scenes."""

import bpy
from mathutils import Vector


def rig():
    scene = bpy.context.scene
    camera_data = bpy.data.cameras.new("Sample exterior lens")
    camera = bpy.data.objects.new("Sample exterior camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (6, -7, 4.2)
    camera.rotation_euler = (
        (Vector((0, 0, 1.55)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    )
    camera_data.lens = 46
    scene.camera = camera
    sun_data = bpy.data.lights.new("Daylight", "SUN")
    sun_data.energy = 2.5
    sun_data.angle = 0.08
    sun = bpy.data.objects.new("Daylight", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = Vector((-4, 5, -7)).to_track_quat("-Z", "Y").to_euler()
    world = bpy.data.worlds.new("Soft sky")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.68, 0.85, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.45
    scene.world = world
    mesh = bpy.data.meshes.new("Sample ground")
    mesh.from_pydata(
        [
            (-100, -100, -0.01),
            (100, -100, -0.01),
            (100, 100, -0.01),
            (-100, 100, -0.01),
        ],
        [],
        [(0, 1, 2, 3)],
    )
    ground = bpy.data.objects.new("Sample ground", mesh)
    scene.collection.objects.link(ground)
    mat = bpy.data.materials.new("Sample earth")
    mat.diffuse_color = (0.065, 0.075, 0.045, 1)
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs[
        "Base Color"
    ].default_value = mat.diffuse_color
    mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.95
    ground.data.materials.append(mat)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 800
    scene.render.resolution_y = 650
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    return camera
