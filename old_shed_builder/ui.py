"""Sidebar panels; geometry changes only when an explicit update is requested."""

import json
import bpy
from .visibility import PARTS


class SHED_PT_main(bpy.types.Panel):
    bl_label = "Old Shed Builder"
    bl_idname = "SHED_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Old Shed"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene, "old_shed_root")
        row = layout.row(align=True)
        row.operator("shed.load_selected")
        row.operator("shed.new")
        layout.operator("shed.generate", icon="FILE_REFRESH")
        layout.prop(scene, "old_shed_scope")
        layout.operator("shed.update")
        layout.prop(
            scene.old_shed_settings, "preserve_edits", text="Preserve User Edits"
        )
        row = layout.row(align=True)
        row.operator("shed.randomize")
        row.operator("shed.reset")
        layout.operator("shed.preset", icon="PRESET")
        layout.operator("shed.bake", icon="MESH_DATA")


GROUPS = [
    ("Dimensions", ("width", "length", "wall_height", "foundation_height")),
    (
        "Framing",
        (
            "stud_width",
            "stud_depth",
            "stud_spacing",
            "header_depth",
            "joist_depth",
            "joist_spacing",
            "floor_thickness",
        ),
    ),
    (
        "Cladding",
        (
            "plank_width",
            "plank_thickness",
            "plank_gap",
            "gap_randomizer",
            "gap_weight",
            "crooked",
        ),
    ),
    (
        "Roof",
        (
            "roof_pitch",
            "overhang",
            "rafter_depth",
            "rafter_spacing",
            "ridge_thickness",
            "collar_ties",
            "sheathing",
        ),
    ),
    (
        "Wood deformation",
        (
            "bow",
            "twist",
            "cup",
            "edge",
            "split",
            "broken",
            "broken_max_percent",
            "loose",
            "separation",
            "seed",
            "variation",
        ),
    ),
    ("Materials", ("aging", "roughness", "grain", "dirt", "water", "color_variation")),
]


def make_panel(title, fields):
    def draw(self, context):
        col = self.layout.column(align=True)
        for name in fields:
            col.prop(context.scene.old_shed_settings, name)

    name = "SHED_PT_" + title.lower().replace(" ", "_")
    return type(
        name,
        (bpy.types.Panel,),
        dict(
            bl_label=title,
            bl_idname=name,
            bl_parent_id="SHED_PT_main",
            bl_space_type="VIEW_3D",
            bl_region_type="UI",
            bl_category="Old Shed",
            bl_options={"DEFAULT_CLOSED"},
            draw=draw,
        ),
    )


class SHED_PT_openings(bpy.types.Panel):
    bl_label = "Door and windows"
    bl_idname = "SHED_PT_openings"
    bl_parent_id = "SHED_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Old Shed"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        p = context.scene.old_shed_settings
        layout = self.layout
        for key, label in (
            ("door", "Door"),
            ("window_a", "Window A"),
            ("window_b", "Window B"),
        ):
            box = layout.box()
            box.label(text=label)
            op = getattr(p, key)
            box.prop(op, "enabled")
            col = box.column()
            col.enabled = op.enabled
            for prop in ("wall", "position", "width", "height"):
                col.prop(op, prop)
            if key != "door":
                col.prop(op, "bottom")
        layout.label(text="Door header height follows Stud width.")
        for prop in ("door_hinge", "door_angle", "glass", "broken_glass", "shutters"):
            layout.prop(p, prop)


class SHED_PT_visibility(bpy.types.Panel):
    bl_label = "Cinematic Visibility"
    bl_idname = "SHED_PT_visibility"
    bl_parent_id = "SHED_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Old Shed"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        layout.enabled = scene.old_shed_root is not None
        row = layout.row()
        row.label(text="Component")
        row.label(text="Viewport / Render")
        for part in PARTS:
            row = layout.row(align=True)
            row.label(text=part.replace("_", " ").title())
            row.prop(
                scene.old_shed_visibility, part + "_viewport", text="", icon="HIDE_OFF"
            )
            row.prop(
                scene.old_shed_visibility,
                part + "_render",
                text="",
                icon="RESTRICT_RENDER_OFF",
            )
        layout.separator()
        layout.prop(scene, "old_shed_profile_name")
        layout.operator("shed.profile_save")
        layout.prop(scene, "old_shed_auto_profiles")
        layout.label(text="Profiles store both viewport and render states.")
        if scene.old_shed_root:
            for name in json.loads(scene.old_shed_root.get("shed_profiles", "{}")):
                layout.operator(
                    "shed.profile_restore", text="Restore: " + name
                ).profile = name


class SHED_PT_leakage(bpy.types.Panel):
    bl_label = "Light leakage"
    bl_idname = "SHED_PT_leakage"
    bl_parent_id = "SHED_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Old Shed"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        p = context.scene.old_shed_settings
        layout = self.layout
        for prop in (
            "leakage",
            "leak_gap",
            "leak_variation",
            "large_gaps",
            "missing",
            "leak_loose",
            "leak_separation",
            "leak_seed",
            "dramatic",
        ):
            layout.prop(p, prop)
        for wall in ("Front", "Rear", "Left", "Right"):
            box = layout.box()
            box.label(text=wall)
            leak = getattr(p, "leak_" + wall.lower())
            box.prop(leak, "override")
            if leak.override:
                for name in (
                    "amount",
                    "gap",
                    "variation",
                    "large_probability",
                    "missing",
                    "loose",
                    "separation",
                ):
                    box.prop(leak, name)


CLASSES = (
    (SHED_PT_main,)
    + tuple(make_panel(*group) for group in GROUPS)
    + (SHED_PT_openings, SHED_PT_visibility, SHED_PT_leakage)
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
