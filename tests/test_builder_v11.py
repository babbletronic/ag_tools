"""Blender integration checks for handing, damage, gaps, crookedness and UV nets."""

import sys, math, json, unittest
from pathlib import Path
from collections import Counter, defaultdict
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bpy
from mathutils import Vector
import old_shed_builder
from old_shed_builder import generator, uvs, wood, cladding, crooked, properties
from old_shed_builder.model import Settings, validate
from old_shed_builder.geometry import box

old_shed_builder.register()


def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for mesh in list(bpy.data.meshes):
        if not mesh.users:
            bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        if not mat.users:
            bpy.data.materials.remove(mat)


def keymap(root):
    return {o["shed_key"]: o for o in generator.owned(root)}


def uv_area(points):
    return (
        sum(a[0] * b[1] - a[1] * b[0] for a, b in zip(points, points[1:] + points[:1]))
        / 2
    )


def assert_atlases(test, objects):
    groups = defaultdict(list)
    for obj in objects:
        if obj.type != "MESH":
            continue
        group = obj["shed_uv_group"]
        groups[group].append(obj)
        layer = obj.data.uv_layers.get("UVMap")
        test.assertIsNotNone(layer, obj.name)
        test.assertTrue(layer.active_render)
        test.assertTrue(
            all(
                -1e-7 <= v.uv.x <= 1 + 1e-7 and -1e-7 <= v.uv.y <= 1 + 1e-7
                for v in layer.data
            ),
            obj.name,
        )
        for face in obj.data.polygons:
            points = [tuple(layer.data[i].uv) for i in face.loop_indices]
            test.assertGreater(uv_area(points), 1e-14, obj.name + f" face {face.index}")
        test.assertEqual(obj.data.materials[0]["shed_uv_group"], group)
    for group, members in groups.items():
        for i, a in enumerate(members):
            for b in members[i + 1 :]:
                test.assertFalse(
                    uvs.intersect(tuple(a["shed_uv_rect"]), tuple(b["shed_uv_rect"])),
                    group + " " + a.name + " " + b.name,
                )
    return groups


class Features(unittest.TestCase):
    def setUp(self):
        clear()

    def test_reference_connected_net_for_board_and_stud(self):
        root = bpy.data.objects.new("Test controls", None)
        bpy.context.scene.collection.objects.link(root)
        ctx = SimpleNamespace(root=root, owner="test", component="framing", objects=[])
        col = bpy.context.scene.collection
        plank = wood.board(
            ctx, "test.board", 2, 0.2, 0.02, col, (0, 0, 0), (1, 0, 0), (0, 1, 0)
        )
        stud = box(ctx, "test.stud", (0, 0, 0), (0.02, 0.2, 2), col)
        for obj in (plank, stud):
            uvs.unwrap(obj)
            layer = obj.data.uv_layers["UVMap"]
            self.assertAlmostEqual(obj["shed_uv_chart_size"][0], 2.04, places=5)
            self.assertAlmostEqual(obj["shed_uv_chart_size"][1], 0.44, places=5)
            # Six macro-faces form one connected island via five non-seam joins.
            adjacency = defaultdict(set)
            uses = defaultdict(list)
            for face in obj.data.polygons:
                for loop in face.loop_indices:
                    uses[obj.data.loops[loop].edge_index].append(face.index)
            for edge, faces in uses.items():
                if not obj.data.edges[edge].use_seam and len(faces) == 2:
                    adjacency[faces[0]].add(faces[1])
                    adjacency[faces[1]].add(faces[0])
            seen = {0}
            todo = [0]
            while todo:
                for nxt in adjacency[todo.pop()] - seen:
                    seen.add(nxt)
                    todo.append(nxt)
            self.assertEqual(len(seen), len(obj.data.polygons))
            # Exactly the reference's front/top/back/bottom strip and side end caps.
            samples = [
                (0.02, 0),
                (2.02, 0.2),
                (0.02, 0.22),
                (2.02, 0.42),
                (0.02, 0.44),
                (0, 0),
                (2.04, 0.2),
            ]
            points = [tuple(d.uv) for d in layer.data]
            for target in samples:
                self.assertTrue(
                    any(
                        abs(p[0] - target[0]) < 1e-5 and abs(p[1] - target[1]) < 1e-5
                        for p in points
                    ),
                    target,
                )

    def test_uv_atlases_cover_all_components_and_are_deterministic(self):
        s = Settings()
        root = generator.generate(s)
        groups = assert_atlases(self, generator.owned(root))
        self.assertTrue(
            {
                "Cladding",
                "Framing",
                "RoofSheathing",
                "DoorsWindows",
                "Floorboards",
                "RoofCovering",
            }
            <= groups.keys()
        )
        self.assertEqual(len([g for g in groups if g.startswith("Glass.")]), 8)
        for members in groups.values():
            self.assertEqual(
                len({o.data.materials[0].as_pointer() for o in members}), 1
            )
            self.assertEqual(len({o["shed_uv_scale"] for o in members}), 1)
        before = {
            o["shed_key"]: tuple(tuple(d.uv) for d in o.data.uv_layers["UVMap"].data)
            for o in generator.owned(root)
            if o.type == "MESH"
        }
        generator.generate(s, root=root)
        after = {
            o["shed_key"]: tuple(tuple(d.uv) for d in o.data.uv_layers["UVMap"].data)
            for o in generator.owned(root)
            if o.type == "MESH"
        }
        self.assertEqual(before, after)

    def test_uv_edits_are_reserved_during_rebuild(self):
        s = Settings()
        root = generator.generate(s)
        obj = next(
            o for o in generator.owned(root) if o.get("shed_uv_group") == "Cladding"
        )
        pointer = obj.as_pointer()
        obj.data.uv_layers["UVMap"].data[0].uv.x += 0.00001
        before = tuple(tuple(d.uv) for d in obj.data.uv_layers["UVMap"].data)
        s.crooked = 0.6
        generator.generate(s, root=root)
        self.assertEqual(obj.as_pointer(), pointer)
        self.assertEqual(
            tuple(tuple(d.uv) for d in obj.data.uv_layers["UVMap"].data), before
        )
        assert_atlases(self, generator.owned(root))

    def test_door_hands_and_header_follow_stud_width(self):
        root = None
        for wall in ("Front", "Rear", "Left", "Right"):
            hinges = []
            for hand in ("LEFT", "RIGHT"):
                s = Settings()
                s.window_a.enabled = False
                s.window_b.enabled = False
                s.door.wall = wall
                s.door.position = s.span(wall) / 2
                s.door_hinge = hand
                s.door_angle = 50
                s.preserve_edits = False
                s.stud_width = 0.05
                s.stud_depth = 0.11
                root = generator.generate(s, root=root)
                objects = keymap(root)
                bpy.context.view_layer.update()
                pivot = objects[f"{wall}.door.pivot"]
                hinges.append(pivot.location.copy())
                outward = Vector(
                    {
                        "Front": (0, -1, 0),
                        "Rear": (0, 1, 0),
                        "Left": (-1, 0, 0),
                        "Right": (1, 0, 0),
                    }[wall]
                )
                leaf = objects[f"{wall}.door.leaf.02"]
                center = sum(
                    (leaf.matrix_world @ v.co for v in leaf.data.vertices), Vector()
                ) / len(leaf.data.vertices)
                self.assertGreater(
                    (center - pivot.matrix_world.translation).dot(outward), 0.05
                )
                header = objects[f"{wall}.door.header"]
                self.assertAlmostEqual(
                    max(v.co.z for v in header.data.vertices)
                    - min(v.co.z for v in header.data.vertices),
                    s.stud_width,
                    places=6,
                )
                pin = objects[f"{wall}.door.hinge.0"]
                self.assertAlmostEqual(
                    (pin.location - pivot.location).dot(outward), 0, places=6
                )
                handle = objects[f"{wall}.door.handle"]
                self.assertGreater(handle.location.length, 0.3)
            # Left/right as viewed from outside, not local-coordinate sign.
            view_right = Vector(
                {
                    "Front": (1, 0, 0),
                    "Rear": (-1, 0, 0),
                    "Left": (0, -1, 0),
                    "Right": (0, 1, 0),
                }[wall]
            )
            self.assertGreater((hinges[1] - hinges[0]).dot(view_right), 0.7)

    def test_damage_uses_both_ends_with_combined_percentage_cap(self):
        s = Settings()
        s.broken = 1
        s.broken_max_percent = 70
        s.variation = 1
        s.split = 0
        s.bow = 0
        s.twist = 0
        s.edge = 0
        s.cup = 0
        s.loose = 0
        root = generator.generate(s)
        modes = Counter()
        for obj in generator.owned(root):
            if not obj.get("shed_plank"):
                continue
            modes[obj["shed_break_mode"]] += 1
            length = obj["shed_length"]
            first = obj["shed_break_start"]
            last = obj["shed_break_end"]
            self.assertLessEqual((first + last) / length, 0.7000001)
            self.assertGreaterEqual(min(v.co.x for v in obj.data.vertices), -1e-6)
            self.assertLessEqual(max(v.co.x for v in obj.data.vertices), length + 1e-6)
            self.assertGreaterEqual(
                max(v.co.x for v in obj.data.vertices)
                - min(v.co.x for v in obj.data.vertices),
                0.3 * length - 1e-6,
            )
            if obj["shed_break_mode"] == "START":
                self.assertEqual(last, 0)
            if obj["shed_break_mode"] == "END":
                self.assertEqual(first, 0)
        self.assertTrue(all(modes[k] > 10 for k in ("START", "END", "BOTH")), modes)
        self.assertNotIn("NONE", modes)

    def test_weighted_gaps_are_bounded_and_monotonic(self):
        s = Settings()
        s.leakage = 0
        s.plank_gap = 0.04
        s.gap_randomizer = 1
        means = []
        for weight in (0.2, 1, 5):
            s.gap_weight = weight
            gaps = [cladding.course_gap(s, "Front", i) for i in range(2000)]
            self.assertTrue(all(0 <= g <= s.plank_gap for g in gaps))
            self.assertEqual(
                gaps, [cladding.course_gap(s, "Front", i) for i in range(2000)]
            )
            means.append(sum(gaps) / len(gaps))
        self.assertLess(means[0], 0.009)
        self.assertGreater(means[2], 0.03)
        self.assertLess(means[0], means[1])
        self.assertLess(means[1], means[2])
        s.gap_randomizer = 0
        self.assertEqual(cladding.course_gap(s, "Front", 0), s.plank_gap)
        s.plank_gap = 0
        s.gap_randomizer = 1
        self.assertEqual(cladding.course_gap(s, "Front", 0), 0)

    def test_crooked_boards_fit_neighbor_gaps_and_opening_bounds(self):
        s = Settings()
        s.crooked = 1
        s.gap_randomizer = 1
        s.gap_weight = 2
        s.plank_gap = 0.025
        s.leakage = 0
        s.variation = 0
        root = generator.generate(s)
        boards = [o for o in generator.owned(root) if o.get("shed_wall")]
        self.assertGreater(
            sum(abs(o.get("shed_crooked_angle", 0)) > 0.01 for o in boards), 10
        )
        polygons = {o: crooked.silhouette(o, s) for o in boards}
        for obj in boards:
            poly = polygons[obj]
            a, b, low, high = obj["shed_plan_bounds"]
            self.assertGreaterEqual(min(p[0] for p in poly), a - 1e-5)
            self.assertLessEqual(max(p[0] for p in poly), b + 1e-5)
            self.assertGreaterEqual(min(p[1] for p in poly), -1e-5)
            for other in boards:
                if other == obj or other["shed_wall"] != obj["shed_wall"]:
                    continue
                if other["shed_plan_bounds"][2] >= high - 1e-6:
                    gap = crooked.clearance(poly, polygons[other], True)
                    if gap is not None:
                        self.assertGreaterEqual(
                            gap, -2e-6, obj.name + " / " + other.name
                        )
        assert_atlases(self, generator.owned(root))
        ROOT.joinpath("artifacts").mkdir(exist_ok=True)
        bpy.context.scene.old_shed_root = root
        bpy.ops.wm.save_as_mainfile(
            filepath=str(ROOT / "artifacts" / "v11_crooked_uv.blend")
        )

    def test_new_settings_roundtrip_and_validation(self):
        s = Settings()
        s.door_hinge = "RIGHT"
        s.broken_max_percent = 65
        s.gap_randomizer = 0.8
        s.gap_weight = 2.4
        s.crooked = 0.6
        properties.to_rna(bpy.context.scene.old_shed_settings, s)
        restored = properties.from_rna(bpy.context.scene.old_shed_settings)
        self.assertEqual(restored.door_hinge, "RIGHT")
        self.assertAlmostEqual(restored.broken_max_percent, 65)
        self.assertAlmostEqual(restored.gap_weight, 2.4, places=5)
        self.assertAlmostEqual(restored.crooked, 0.6, places=5)
        legacy = Settings().to_dict()
        for key in (
            "door_hinge",
            "broken_max_percent",
            "gap_randomizer",
            "gap_weight",
            "crooked",
        ):
            del legacy[key]
        validate(Settings.from_dict(legacy))
        for key, value in (
            ("door_hinge", "UP"),
            ("broken_max_percent", 100),
            ("gap_weight", 0),
            ("crooked", 2),
        ):
            invalid = Settings()
            setattr(invalid, key, value)
            with self.assertRaises(ValueError):
                validate(invalid)


result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(Features)
)
if not result.wasSuccessful():
    raise SystemExit(1)
print("V1.1 FEATURE REGRESSIONS PASS")
