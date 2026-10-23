"""Integration regressions executed by real Blender, never a mocked bpy."""

import json, math, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bpy
import bmesh
import old_shed_builder
from old_shed_builder import generator, properties, visibility, presets
from old_shed_builder.model import Settings, validate

old_shed_builder.register()


def clear():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        if mat.users == 0:
            bpy.data.materials.remove(mat)
    visibility._last_camera.clear()


def vertices(obj):
    return tuple(tuple(v.co) for v in obj.data.vertices)


def by_key(root):
    return {o["shed_key"]: o for o in generator.owned(root)}


class Production(unittest.TestCase):
    def setUp(self):
        clear()
        self.s = Settings()
        self.root = generator.generate(self.s)
        bpy.context.scene.old_shed_root = self.root

    def test_deterministic_rebuild_and_no_leaked_data(self):
        before = {
            k: vertices(o) for k, o in by_key(self.root).items() if o.type == "MESH"
        }
        counts = (
            len(bpy.data.objects),
            len(bpy.data.meshes),
            len(bpy.data.collections),
            len(bpy.data.materials),
        )
        generator.generate(self.s, root=self.root)
        after = {
            k: vertices(o) for k, o in by_key(self.root).items() if o.type == "MESH"
        }
        self.assertEqual(before, after)
        self.assertEqual(self.root["shed_preserved_count"], 0)
        self.assertEqual(
            counts,
            (
                len(bpy.data.objects),
                len(bpy.data.meshes),
                len(bpy.data.collections),
                len(bpy.data.materials),
            ),
        )

    def test_preserve_mesh_edits_and_unrelated_objects(self):
        obj = next(o for o in generator.owned(self.root) if ".siding." in o["shed_key"])
        key = obj["shed_key"]
        ptr = obj.as_pointer()
        obj.data.vertices[0].co.z += 0.02
        marker = bpy.data.objects.new("User authored object", None)
        obj.users_collection[0].objects.link(marker)
        extra = bpy.data.collections.new("User shot collection")
        bpy.context.scene.collection.children.link(extra)
        other = next(
            o for o in generator.owned(self.root) if "floor.joist." in o["shed_key"]
        )
        extra.objects.link(other)
        other_key = other["shed_key"]
        generator.generate(self.s, root=self.root)
        self.assertEqual(by_key(self.root)[key].as_pointer(), ptr)
        self.assertIn(marker.name, bpy.data.objects)
        self.assertIn(by_key(self.root)[other_key].name, extra.objects)
        self.assertGreater(self.root["shed_preserved_count"], 0)
        self.s.preserve_edits = False
        generator.generate(self.s, root=self.root)
        self.assertNotEqual(by_key(self.root)[key].as_pointer(), ptr)

    def test_preserve_material_edits(self):
        obj = next(o for o in generator.owned(self.root) if o.get("shed_plank"))
        key = obj["shed_key"]
        pointer = obj.as_pointer()
        mat = obj.data.materials[0]
        shader = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        shader.inputs["Roughness"].default_value = 0.21
        generator.generate(self.s, root=self.root)
        self.assertEqual(by_key(self.root)[key].as_pointer(), pointer)
        self.assertEqual(by_key(self.root)[key].data.materials[0], mat)

    def test_preserve_hinged_assembly_and_root_transform(self):
        objects = by_key(self.root)
        pivot = objects["Front.door.pivot"]
        ptr = pivot.as_pointer()
        pivot.rotation_euler.z -= 0.2
        self.root.location = (10, 5, 2)
        self.root.rotation_euler.z = 0.3
        generator.generate(self.s, root=self.root)
        self.assertEqual(by_key(self.root)["Front.door.pivot"].as_pointer(), ptr)
        self.assertEqual(tuple(self.root.location), (10, 5, 2))
        self.assertTrue(
            all(
                o.parent == pivot
                for o in generator.owned(self.root)
                if ".door.leaf." in o["shed_key"]
            )
        )

    def test_selective_scopes_and_rna_float_roundtrip(self):
        initial = by_key(self.root)
        frame = initial["Front.plate.top.0"].as_pointer()
        board_key = next(k for k in initial if ".siding." in k)
        board_ptr = initial[board_key].as_pointer()
        s = properties.from_rna(bpy.context.scene.old_shed_settings)
        s.aging = 0.2
        generator.generate(s, root=self.root, scope="MATERIALS")
        self.assertEqual(by_key(self.root)[board_key].as_pointer(), board_ptr)
        s.leakage = 0.6
        generator.generate(s, root=self.root, scope="CLADDING")
        self.assertEqual(by_key(self.root)["Front.plate.top.0"].as_pointer(), frame)
        self.assertNotEqual(by_key(self.root)[board_key].as_pointer(), board_ptr)
        s.width += 0.5
        with self.assertRaisesRegex(ValueError, "Rebuild All"):
            generator.generate(s, root=self.root, scope="CLADDING")

    def test_transaction_failure_leaves_scene_intact(self):
        counts = (
            len(bpy.data.objects),
            len(bpy.data.meshes),
            len(bpy.data.collections),
        )
        before = {k: o.as_pointer() for k, o in by_key(self.root).items()}
        fn = generator.cladding.build

        def fail(*args):
            raise RuntimeError("Injected construction failure")

        generator.cladding.build = fail
        try:
            with self.assertRaisesRegex(RuntimeError, "Injected"):
                generator.generate(self.s, root=self.root)
        finally:
            generator.cladding.build = fn
        self.assertEqual(
            before, {k: o.as_pointer() for k, o in by_key(self.root).items()}
        )
        self.assertEqual(
            counts,
            (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.collections)),
        )

    def test_normals_thickness_and_topology(self):
        for obj in generator.owned(self.root):
            if obj.type != "MESH":
                continue
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            self.assertTrue(all(e.is_manifold for e in bm.edges), obj.name)
            self.assertGreater(bm.calc_volume(signed=True), 0, obj.name)
            self.assertTrue(all(f.calc_area() > 1e-10 for f in bm.faces), obj.name)
            bm.free()
            if obj.get("shed_plank"):
                layer = len(obj.data.vertices) // 2
                for a, b in zip(obj.data.vertices[:layer], obj.data.vertices[layer:]):
                    self.assertAlmostEqual(
                        (b.co - a.co).length, obj["shed_thickness"], places=5
                    )

    def test_openings_are_clear_and_headers_bear(self):
        bpy.context.view_layer.update()
        for name, op in [
            ("door", self.s.door),
            ("window_a", self.s.window_a),
            ("window_b", self.s.window_b),
        ]:
            a = op.position - op.width / 2
            b = op.position + op.width / 2
            for obj in generator.owned(self.root):
                if obj.get("shed_component") != "framing" or not obj[
                    "shed_key"
                ].startswith(op.wall + "."):
                    continue
                coords = [obj.matrix_local @ v.co for v in obj.data.vertices]
                axis = 0 if op.wall in ("Front", "Rear") else 1
                span = self.s.span(op.wall)
                lo = min(v[axis] for v in coords) + span / 2
                hi = max(v[axis] for v in coords) + span / 2
                zlo = min(v.z for v in coords) - self.s.floor_z
                zhi = max(v.z for v in coords) - self.s.floor_z
                intersects = (
                    min(hi, b) - max(lo, a) > 1e-5
                    and min(zhi, op.bottom + op.height) - max(zlo, op.bottom) > 1e-5
                )
                self.assertFalse(intersects, obj.name)
            header = by_key(self.root)[f"{op.wall}.{name}.header"]
            jack = by_key(self.root)[f"{op.wall}.{name}.jack.L"]
            self.assertAlmostEqual(
                min(v.co.z for v in header.data.vertices) + header.location.z,
                max(v.co.z for v in jack.data.vertices) + jack.location.z,
                places=5,
            )

    def test_visibility_and_camera_profiles_are_nondestructive(self):
        count = len(bpy.data.objects)
        hashes = {
            o["shed_key"]: generator.fingerprint(o) for o in generator.owned(self.root)
        }
        camera_a = bpy.data.objects.new("Shot A", bpy.data.cameras.new("Lens A"))
        camera_b = bpy.data.objects.new("Shot B", bpy.data.cameras.new("Lens B"))
        for camera in (camera_a, camera_b):
            bpy.context.scene.collection.objects.link(camera)
        visibility.save_profile(self.root, "Exterior", camera_a)
        visibility.set_part(self.root, "front", False, False)
        visibility.set_part(self.root, "roof_covering", False, True)
        visibility.save_profile(self.root, "Interior", camera_b)
        scene = bpy.context.scene
        scene["shed_auto_profiles"] = True
        scene.camera = camera_a
        visibility.camera_changed(scene)
        self.assertTrue(visibility.state(self.root)["front"]["render"])
        scene.camera = camera_b
        visibility.camera_changed(scene)
        self.assertFalse(visibility.state(self.root)["front"]["render"])
        self.assertFalse(scene.old_shed_visibility.front_render)
        front = next(c for c in bpy.data.collections if c.get("shed_tag") == "Front")
        self.assertTrue(front.hide_render)  # excludes all rays, including shadow rays
        self.assertEqual(count + 2, len(bpy.data.objects))
        self.assertEqual(
            hashes,
            {
                o["shed_key"]: generator.fingerprint(o)
                for o in generator.owned(self.root)
            },
        )

    def test_leakage_wall_override_and_independent_seed(self):
        before = {
            k: vertices(o) for k, o in by_key(self.root).items() if ".siding." in k
        }
        self.s.walls["Front"].override = True
        self.s.walls["Front"].amount = 1
        self.s.walls["Front"].gap = 0.04
        self.s.walls["Front"].missing = 0.2
        generator.generate(self.s, root=self.root, scope="CLADDING")
        after = {
            k: vertices(o) for k, o in by_key(self.root).items() if ".siding." in k
        }
        self.assertEqual(
            {k: v for k, v in before.items() if k.startswith("Rear.")},
            {k: v for k, v in after.items() if k.startswith("Rear.")},
        )
        self.assertNotEqual(
            {k: v for k, v in before.items() if k.startswith("Front.")},
            {k: v for k, v in after.items() if k.startswith("Front.")},
        )

    def test_bake_is_independent_and_does_not_double_render(self):
        self.root.location.x = 3
        bpy.context.view_layer.update()
        source = by_key(self.root)
        baked = generator.bake(self.root)
        self.assertTrue(baked.hide_render and baked.hide_viewport)
        meshes = [o for o in baked.objects if o.type == "MESH"]
        self.assertEqual(len(meshes), sum(o.type == "MESH" for o in source.values()))
        for obj in meshes:
            original = source[obj.name.removeprefix("Baked ")]
            self.assertNotEqual(obj.data, original.data)
            self.assertNotEqual(obj.data.materials[0], original.data.materials[0])
            self.assertFalse(obj.get("shed_owner"))
            self.assertEqual(obj.matrix_world, original.matrix_world)

    def test_invalid_parameters_are_rejected_before_changes(self):
        count = len(bpy.data.objects)
        for mutate in (
            lambda s: setattr(s, "width", float("nan")),
            lambda s: setattr(s.window_a, "wall", "Nowhere"),
            lambda s: setattr(s.door, "position", 0.01),
            lambda s: setattr(s, "leakage", 1.5),
            lambda s: (setattr(s, "roof_pitch", 60), setattr(s, "rafter_depth", 0.06)),
            lambda s: setattr(s.window_a, "bottom", 2.0),
        ):
            bad = Settings()
            mutate(bad)
            with self.assertRaises(ValueError):
                generator.generate(bad, root=self.root)
            self.assertEqual(count, len(bpy.data.objects))
        bad = Settings()
        bad.window_a.wall = "Front"
        bad.window_a.position = bad.door.position
        with self.assertRaisesRegex(ValueError, "overlaps"):
            validate(bad)

    def test_door_on_each_wall_and_animated_pivot(self):
        for wall in ("Front", "Rear", "Left", "Right"):
            s = Settings()
            s.window_a.enabled = False
            s.window_b.enabled = False
            s.door.wall = wall
            s.door.position = s.span(wall) / 2
            s.door_angle = 35
            s.preserve_edits = False
            generator.generate(s, root=self.root)
            bpy.context.view_layer.update()
            objects = by_key(self.root)
            pivot = objects[f"{wall}.door.pivot"]
            leaf = objects[f"{wall}.door.leaf.02"]
            normal = {
                "Front": (0, -1, 0),
                "Rear": (0, 1, 0),
                "Left": (-1, 0, 0),
                "Right": (1, 0, 0),
            }[wall]
            from mathutils import Vector

            center = sum(
                (leaf.matrix_world @ v.co for v in leaf.data.vertices), Vector()
            ) / len(leaf.data.vertices)
            self.assertGreater(
                (center - pivot.matrix_world.translation).dot(Vector(normal)), 0.05
            )
        pivot.keyframe_insert(data_path="rotation_euler", frame=1)
        pointer = pivot.as_pointer()
        s.preserve_edits = True
        generator.generate(s, root=self.root)
        self.assertEqual(by_key(self.root)["Right.door.pivot"].as_pointer(), pointer)

    def test_heavy_damage_retains_solid_boards(self):
        s = Settings()
        s.variation = 1
        s.twist = 12
        s.bow = 0.06
        s.cup = 0.02
        s.edge = 0.008
        s.split = 0.3
        s.broken = 1
        s.loose = 1
        s.separation = 0.15
        s.leakage = 1
        s.dramatic = True
        s.leak_gap = 0.06
        generator.generate(s, root=self.root)
        for obj in generator.owned(self.root):
            if not obj.get("shed_plank"):
                continue
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            self.assertTrue(all(e.is_manifold for e in bm.edges), obj.name)
            self.assertGreater(bm.calc_volume(signed=True), 0, obj.name)
            self.assertTrue(all(f.calc_area() > 1e-10 for f in bm.faces), obj.name)
            bm.free()

    def test_registered_ui_operators(self):
        scene = bpy.context.scene
        self.assertEqual(bpy.ops.shed.update(), {"FINISHED"})
        scene.old_shed_scope = "MATERIALS"
        scene.old_shed_settings.aging = 0.5
        self.assertEqual(bpy.ops.shed.update(), {"FINISHED"})
        self.assertEqual(bpy.ops.shed.profile_save(), {"FINISHED"})
        self.assertEqual(
            bpy.ops.shed.profile_restore(profile="Camera setup"), {"FINISHED"}
        )

    def test_preset_and_new_dimensions(self):
        s = presets.dilapidated()
        s.width = 4
        s.length = 5
        s.wall_height = 2.8
        s.roof_pitch = 40
        s.rafter_depth = 0.18
        generator.generate(s, root=self.root)
        self.assertEqual(json.loads(self.root["shed_settings"])["width"], 4)
        self.assertGreater(len(generator.owned(self.root)), 300)


result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(Production)
)
if not result.wasSuccessful():
    raise SystemExit(1)
# Save and reopen within a separate Blender process via test_persistence.py.
clear()
root = generator.generate(presets.dilapidated())
bpy.context.scene.old_shed_root = root
visibility.save_profile(root, "Exterior")
sys.path.insert(0, str(ROOT / "tests"))
from scene_support import rig

rig()
ROOT.joinpath("artifacts").mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "artifacts" / "stage_10.blend"))
old_shed_builder.unregister()
old_shed_builder.register()
old_shed_builder.unregister()
print("Registration/unregistration/re-registration PASS")
