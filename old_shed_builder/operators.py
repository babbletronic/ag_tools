import json
import bpy
from bpy.props import StringProperty
from . import generator, properties, visibility, presets
from .model import Settings


def execute_build(operator, context, scope="ALL"):
    if context.mode != "OBJECT":
        operator.report({"ERROR"}, "Switch to Object Mode before rebuilding")
        return {"CANCELLED"}
    scene = context.scene
    try:
        root = generator.generate(
            properties.from_rna(scene.old_shed_settings),
            root=scene.old_shed_root,
            scope=scope,
        )
        scene.old_shed_root = root
        properties.sync_visibility(scene)
        count = root.get("shed_preserved_count", 0)
        operator.report({"INFO"}, f"Shed updated; {count} edited objects retained")
        return {"FINISHED"}
    except (ValueError, RuntimeError) as exc:
        operator.report({"ERROR"}, str(exc))
        return {"CANCELLED"}


class SHED_OT_generate(bpy.types.Operator):
    bl_idname = "shed.generate"
    bl_label = "Generate / Rebuild"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        return execute_build(self, context)


class SHED_OT_update(bpy.types.Operator):
    bl_idname = "shed.update"
    bl_label = "Update Parameters"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        return execute_build(self, context, context.scene.old_shed_scope)


class SHED_OT_new(bpy.types.Operator):
    bl_idname = "shed.new"
    bl_label = "New Shed"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        previous = context.scene.old_shed_root
        context.scene.old_shed_root = None
        result = execute_build(self, context)
        if result == {"CANCELLED"}:
            context.scene.old_shed_root = previous
        return result


class SHED_OT_selected(bpy.types.Operator):
    bl_idname = "shed.load_selected"
    bl_label = "Load Selected Shed"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.object
        owner = obj.get("shed_owner") if obj else None
        root = next(
            (
                o
                for o in context.scene.objects
                if o.get("shed_root") and o.get("shed_owner") == owner
            ),
            None,
        )
        if not root:
            self.report({"ERROR"}, "Select a generated shed object first")
            return {"CANCELLED"}
        context.scene.old_shed_root = root
        properties.root_changed(context.scene, context)
        return {"FINISHED"}


class SHED_OT_randomize(bpy.types.Operator):
    bl_idname = "shed.randomize"
    bl_label = "Randomize Weathering"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        p = context.scene.old_shed_settings
        p.seed = (p.seed + 7919) % 2147483647
        p.leak_seed = (p.leak_seed + 104729) % 2147483647
        return execute_build(self, context)


class SHED_OT_reset(bpy.types.Operator):
    bl_idname = "shed.reset"
    bl_label = "Reset Weathering"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        p = context.scene.old_shed_settings
        p.variation = 0
        p.leakage = 0
        p.aging = 0.12
        p.dirt = 0
        p.water = 0
        p.roughness = 0.6
        p.broken = 0
        p.loose = 0
        p.missing = 0
        p.leak_loose = 0
        for wall in ("front", "rear", "left", "right"):
            getattr(p, "leak_" + wall).override = False
        return execute_build(self, context)


class SHED_OT_preset(bpy.types.Operator):
    bl_idname = "shed.preset"
    bl_label = "Small Dilapidated Shed"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        properties.to_rna(context.scene.old_shed_settings, presets.dilapidated())
        return execute_build(self, context)


class SHED_OT_bake(bpy.types.Operator):
    bl_idname = "shed.bake"
    bl_label = "Bake to Editable Meshes"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene.old_shed_root is not None

    def execute(self, context):
        c = generator.bake(context.scene.old_shed_root)
        self.report(
            {"INFO"},
            f"Created {c.name}; enable this collection and hide the generator to display it",
        )
        return {"FINISHED"}


class SHED_OT_profile_save(bpy.types.Operator):
    bl_idname = "shed.profile_save"
    bl_label = "Save Visibility for Active Camera"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene.old_shed_root is not None

    def execute(self, context):
        name = context.scene.old_shed_profile_name.strip()
        if not name:
            self.report({"ERROR"}, "Enter a profile name")
            return {"CANCELLED"}
        visibility.save_profile(context.scene.old_shed_root, name, context.scene.camera)
        visibility._last_camera.clear()
        return {"FINISHED"}


class SHED_OT_profile_restore(bpy.types.Operator):
    bl_idname = "shed.profile_restore"
    bl_label = "Restore Profile"
    bl_options = {"REGISTER", "UNDO"}
    profile: StringProperty()

    def execute(self, context):
        try:
            visibility.restore_profile(context.scene.old_shed_root, self.profile)
        except (ValueError, AttributeError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        properties.sync_visibility(context.scene)
        return {"FINISHED"}


CLASSES = (
    SHED_OT_generate,
    SHED_OT_update,
    SHED_OT_new,
    SHED_OT_selected,
    SHED_OT_randomize,
    SHED_OT_reset,
    SHED_OT_preset,
    SHED_OT_bake,
    SHED_OT_profile_save,
    SHED_OT_profile_restore,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
