"""RNA adapters for the persistent dataclass model; parameters do not auto-build."""

import json
from dataclasses import fields
import bpy
from bpy.props import (
    BoolProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
    EnumProperty,
    PointerProperty,
)
from .model import Settings, Opening, Leakage, WALLS
from . import visibility

_syncing = False
WALL_ITEMS = [(w, w, f"{w} wall") for w in WALLS]

RANGES = {
    "width": (1.5, 15),
    "length": (1.5, 20),
    "wall_height": (1.5, 6),
    "foundation_height": (0.05, 0.8),
    "stud_width": (0.025, 0.12),
    "stud_depth": (0.06, 0.25),
    "stud_spacing": (0.2, 1.2),
    "header_depth": (0.08, 0.4),
    "joist_depth": (0.08, 0.4),
    "joist_spacing": (0.2, 1),
    "floor_thickness": (0.015, 0.06),
    "plank_width": (0.08, 0.35),
    "plank_thickness": (0.012, 0.06),
    "plank_gap": (0, 0.05),
    "roof_pitch": (10, 60),
    "overhang": (0.05, 0.8),
    "rafter_depth": (0.06, 0.3),
    "rafter_spacing": (0.25, 1.2),
    "ridge_thickness": (0.025, 0.12),
    "door_angle": (-170, 170),
    "gap_weight": (0.05, 8),
    "broken_max_percent": (0, 95),
    "bow": (0, 0.06),
    "twist": (0, 12),
    "cup": (0, 0.02),
    "edge": (0, 0.008),
    "split": (0, 0.3),
    "separation": (0, 0.15),
    "leak_separation": (0, 0.15),
    "leak_gap": (0, 0.08),
}
DESCRIPTIONS = {
    "width": "Outside width of structural framing, in meters",
    "length": "Outside length of structural framing, in meters",
    "wall_height": "Finished floor to top of double top plate, in meters",
    "plank_gap": "Base construction gap; light leakage adds physical spacing",
    "bow": "Lengthwise bow, limited to 65% of board thickness to limit intersections",
    "cup": "Cross-sectional cup, limited to 35% of board thickness",
    "split": "Maximum end-split length, further limited to 14% of plank length",
    "broken": "Probability of damage at a randomly selected start, end, or both ends",
    "broken_max_percent": "Maximum combined length removed from a board, as percent of original length",
    "gap_randomizer": "Blend from regular spacing (0) to weighted random gaps from zero to the configured maximum (1)",
    "gap_weight": "Below 1 favors no gap; above 1 favors the maximum gap; 1 is uniform",
    "crooked": "Rotate wall boards in-plane within available neighbor gaps; 1 uses the full safe clearance",
    "header_depth": "Window header height; the door header follows Stud width",
    "variation": "Scales wood deformation and damage; zero creates straight sound boards",
    "leakage": "Scales physical gaps, missing pieces and detached ends in siding",
    "dramatic": "Amplifies leakage by 1.8 and permits gaps up to 65% of board width",
    "preserve_edits": "Keep changed owned objects and complete edited fixture assemblies during rebuilds",
    "door_angle": "Door rotation in degrees; positive opens toward the exterior",
    "sheathing": "Solid roof underlayer; hiding Roof Covering hides both roof skins",
}


class ShedOpening(bpy.types.PropertyGroup):
    wall: EnumProperty(name="Wall", items=WALL_ITEMS, default="Front")
    position: FloatProperty(
        name="Center from wall start",
        default=1.5,
        min=0,
        max=20,
        unit="LENGTH",
        description="Measured from the negative X or negative Y end of the wall",
    )
    width: FloatProperty(
        name="Rough opening width", default=0.85, min=0.3, max=8, unit="LENGTH"
    )
    height: FloatProperty(
        name="Rough opening height", default=1.9, min=0.3, max=5, unit="LENGTH"
    )
    bottom: FloatProperty(
        name="Sill above floor", default=0, min=0, max=5, unit="LENGTH"
    )
    enabled: BoolProperty(name="Enabled", default=True)


# Distinct RNA defaults also work in scenes created after add-on registration.
def window_type(name, wall, position):
    annotations = dict(ShedOpening.__annotations__)
    annotations.update(
        {
            "wall": EnumProperty(name="Wall", items=WALL_ITEMS, default=wall),
            "position": FloatProperty(
                name="Center from wall start",
                default=position,
                min=0,
                max=20,
                unit="LENGTH",
            ),
            "width": FloatProperty(
                name="Rough opening width", default=0.8, min=0.3, max=8, unit="LENGTH"
            ),
            "height": FloatProperty(
                name="Rough opening height", default=0.7, min=0.3, max=5, unit="LENGTH"
            ),
            "bottom": FloatProperty(
                name="Sill above floor", default=1.0, min=0, max=5, unit="LENGTH"
            ),
        }
    )
    return type(name, (bpy.types.PropertyGroup,), {"__annotations__": annotations})


ShedWindowA = window_type("ShedWindowA", "Left", 1.5)
ShedWindowB = window_type("ShedWindowB", "Right", 2.6)


class ShedLeakage(bpy.types.PropertyGroup):
    override: BoolProperty(name="Override global leakage", default=False)
    amount: FloatProperty(name="Leakage amount", default=0.35, min=0, max=1)
    gap: FloatProperty(
        name="Average added gap", default=0.006, min=0, max=0.08, unit="LENGTH"
    )
    variation: FloatProperty(name="Gap variation", default=0.5, min=0, max=1)
    large_probability: FloatProperty(
        name="Larger gap probability", default=0.04, min=0, max=1
    )
    missing: FloatProperty(name="Missing board frequency", default=0.025, min=0, max=1)
    loose: FloatProperty(name="Loose board frequency", default=0.06, min=0, max=1)
    separation: FloatProperty(
        name="Detached end separation", default=0.018, min=0, max=0.15, unit="LENGTH"
    )


class ShedSettings(bpy.types.PropertyGroup):
    pass


annotations = {}
for f in fields(Settings):
    if f.name in ("schema", "door", "window_a", "window_b", "walls"):
        continue
    value = getattr(Settings(), f.name)
    name = {
        "gap_weight": "Gap random weight",
        "broken_max_percent": "Max broken length (%)",
        "header_depth": "Window header height",
    }.get(f.name, f.name.replace("_", " ").capitalize())
    kw = {"name": name, "description": DESCRIPTIONS.get(f.name, name)}
    if f.name == "door_hinge":
        prop = EnumProperty(
            name="Door hinge side",
            default=value,
            items=[
                ("LEFT", "Left", "Hinges on the left when viewed from outside"),
                ("RIGHT", "Right", "Hinges on the right when viewed from outside"),
            ],
        )
    elif isinstance(value, bool):
        prop = BoolProperty(default=value, **kw)
    elif isinstance(value, int):
        prop = IntProperty(default=value, min=0, max=2147483647, **kw)
    else:
        low, high = RANGES.get(f.name, (0, 1))
        unit = (
            "LENGTH"
            if f.name in RANGES
            and f.name
            not in (
                "roof_pitch",
                "door_angle",
                "twist",
                "gap_weight",
                "broken_max_percent",
            )
            else "NONE"
        )
        prop = FloatProperty(
            default=value, min=low, max=high, unit=unit, precision=3, **kw
        )
    annotations[f.name] = prop
for key, kind in (
    ("door", ShedOpening),
    ("window_a", ShedWindowA),
    ("window_b", ShedWindowB),
):
    annotations[key] = PointerProperty(type=kind)
for wall in WALLS:
    annotations["leak_" + wall.lower()] = PointerProperty(type=ShedLeakage)
ShedSettings.__annotations__ = annotations


def from_rna(pg):
    data = {
        f.name: getattr(pg, f.name)
        for f in fields(Settings)
        if f.name not in ("schema", "door", "window_a", "window_b", "walls")
    }
    for key in ("door", "window_a", "window_b"):
        data[key] = {f.name: getattr(getattr(pg, key), f.name) for f in fields(Opening)}
    data["walls"] = {
        w: {
            f.name: getattr(getattr(pg, "leak_" + w.lower()), f.name)
            for f in fields(Leakage)
        }
        for w in WALLS
    }
    return Settings.from_dict(data)


def to_rna(pg, s):
    for key, value in s.to_dict().items():
        if key == "schema":
            continue
        if key == "walls":
            for wall, values in value.items():
                for k, v in values.items():
                    setattr(getattr(pg, "leak_" + wall.lower()), k, v)
        elif key in ("door", "window_a", "window_b"):
            for k, v in value.items():
                setattr(getattr(pg, key), k, v)
        else:
            setattr(pg, key, value)


def update_visibility(self, context):
    if _syncing or not context or not context.scene:
        return
    root = context.scene.old_shed_root
    if not root:
        return
    values = {
        part: {
            mode: getattr(self, part + "_" + mode) for mode in ("viewport", "render")
        }
        for part in visibility.PARTS
    }
    visibility.apply(root, values)


class ShedVisibility(bpy.types.PropertyGroup):
    pass


ShedVisibility.__annotations__ = {
    part
    + "_"
    + mode: BoolProperty(
        name=part.replace("_", " ").title() + " " + mode,
        default=True,
        update=update_visibility,
        description=f'Show {part.replace("_"," ")} in {mode}; does not regenerate geometry',
    )
    for part in visibility.PARTS
    for mode in ("viewport", "render")
}


def sync_visibility(scene):
    global _syncing
    root = scene.old_shed_root
    if not root:
        return
    _syncing = True
    try:
        for part, modes in visibility.state(root).items():
            for mode, value in modes.items():
                setattr(scene.old_shed_visibility, part + "_" + mode, value)
    finally:
        _syncing = False


def root_changed(scene, context):
    root = scene.old_shed_root
    if root and root.get("shed_settings"):
        to_rna(
            scene.old_shed_settings,
            Settings.from_dict(json.loads(root["shed_settings"])),
        )
        sync_visibility(scene)


CLASSES = (
    ShedOpening,
    ShedWindowA,
    ShedWindowB,
    ShedLeakage,
    ShedSettings,
    ShedVisibility,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.old_shed_settings = PointerProperty(type=ShedSettings)
    bpy.types.Scene.old_shed_root = PointerProperty(
        name="Active shed",
        type=bpy.types.Object,
        poll=lambda self, obj: bool(obj.get("shed_root")),
        update=root_changed,
    )
    bpy.types.Scene.old_shed_visibility = PointerProperty(type=ShedVisibility)
    bpy.types.Scene.old_shed_scope = EnumProperty(
        name="Update scope",
        default="ALL",
        items=[
            ("ALL", "All components", "Rebuild all dependent geometry"),
            (
                "FRAMING",
                "Framing only",
                "Replace structural members using the last compatible layout",
            ),
            ("CLADDING", "Wall cladding only", "Update siding and light leakage"),
            (
                "MATERIALS",
                "Materials only",
                "Update material controls without replacing meshes",
            ),
        ],
    )
    bpy.types.Scene.old_shed_profile_name = StringProperty(
        name="Profile name", default="Camera setup"
    )
    bpy.types.Scene.old_shed_auto_profiles = BoolProperty(
        name="Follow active camera",
        description="Apply saved viewport AND render visibility when the active camera changes",
        get=lambda scene: scene.get("shed_auto_profiles", False),
        set=lambda scene, value: scene.__setitem__("shed_auto_profiles", value),
    )


def unregister():
    for name in (
        "old_shed_settings",
        "old_shed_root",
        "old_shed_visibility",
        "old_shed_scope",
        "old_shed_profile_name",
        "old_shed_auto_profiles",
    ):
        if hasattr(bpy.types.Scene, name):
            delattr(bpy.types.Scene, name)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
