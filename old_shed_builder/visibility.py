"""Collection visibility: independent viewport/render states and camera profiles.

Hiding uses collection render exclusion, so hidden walls do not cast invisible
shadows. No mesh deletion or generation is performed by this module.
"""

import json
import uuid
import bpy
from bpy.app.handlers import persistent

PARTS = (
    "front",
    "rear",
    "left",
    "right",
    "roof",
    "roof_covering",
    "roof_framing",
    "floor_foundation",
    "cladding",
    "framing",
    "fixtures",
)
_last_camera = {}
_busy = False


def defaults():
    return {name: {"viewport": True, "render": True} for name in PARTS}


def state(root):
    return json.loads(root.get("shed_visibility", json.dumps(defaults())))


def apply(root, values=None):
    values = values or state(root)
    root["shed_visibility"] = json.dumps(values, sort_keys=True)
    for c in bpy.data.collections:
        if c.get("shed_owner") != root.get("shed_owner"):
            continue
        tag = c.get("shed_tag", "")
        keys = []
        if tag in ("Foundation", "Floor"):
            keys = ["floor_foundation"]
        elif tag == "Roof":
            keys = ["roof"]
        elif tag == "Roof.Framing":
            keys = ["roof", "roof_framing"]
        elif tag == "Roof.Covering":
            keys = ["roof", "roof_covering"]
        elif tag in ("Front", "Rear", "Left", "Right"):
            keys = [tag.lower()]
        elif "." in tag:
            wall, part = tag.split(".", 1)
            if wall in ("Front", "Rear", "Left", "Right"):
                keys = [wall.lower(), part.lower()]
        c.hide_viewport = any(not values[k]["viewport"] for k in keys)
        c.hide_render = any(not values[k]["render"] for k in keys)


def set_part(root, part, viewport=None, render=None):
    values = state(root)
    if viewport is not None:
        values[part]["viewport"] = viewport
    if render is not None:
        values[part]["render"] = render
    apply(root, values)


def save_profile(root, name, camera=None):
    profiles = json.loads(root.get("shed_profiles", "{}"))
    camera_id = ""
    if camera:
        if not camera.get("shed_camera_id"):
            camera["shed_camera_id"] = uuid.uuid4().hex
        camera_id = camera["shed_camera_id"]
    if camera_id:
        for profile in profiles.values():
            if profile["camera"] == camera_id:
                profile["camera"] = ""
    profiles[name] = {"visibility": state(root), "camera": camera_id}
    root["shed_profiles"] = json.dumps(profiles, sort_keys=True)


def restore_profile(root, name):
    profiles = json.loads(root.get("shed_profiles", "{}"))
    if name not in profiles:
        raise ValueError(f"Unknown visibility profile: {name}")
    apply(root, profiles[name]["visibility"])


@persistent
def camera_changed(scene, *args):
    global _busy
    if _busy or not scene.get("shed_auto_profiles", False):
        return
    camera = scene.camera
    if not camera:
        return
    camera_id = camera.get("shed_camera_id", "")
    if not camera_id:
        return
    _busy = True
    try:
        for root in scene.objects:
            if not root.get("shed_root"):
                continue
            key = (scene.as_pointer(), root.as_pointer())
            if _last_camera.get(key) == camera_id:
                continue
            for profile in json.loads(root.get("shed_profiles", "{}")).values():
                if profile["camera"] == camera_id:
                    apply(root, profile["visibility"])
                    if getattr(scene, "old_shed_root", None) == root:
                        from .properties import sync_visibility

                        sync_visibility(scene)
                    break
            _last_camera[key] = camera_id
    finally:
        _busy = False


@persistent
def load_post(*args):
    _last_camera.clear()
    for obj in bpy.data.objects:
        if obj.get("shed_root"):
            apply(obj)


def register():
    for handlers, fn in (
        (bpy.app.handlers.depsgraph_update_post, camera_changed),
        (bpy.app.handlers.frame_change_post, camera_changed),
        (bpy.app.handlers.render_pre, camera_changed),
        (bpy.app.handlers.load_post, load_post),
    ):
        if fn not in handlers:
            handlers.append(fn)


def unregister():
    for handlers, fn in (
        (bpy.app.handlers.depsgraph_update_post, camera_changed),
        (bpy.app.handlers.frame_change_post, camera_changed),
        (bpy.app.handlers.render_pre, camera_changed),
        (bpy.app.handlers.load_post, load_post),
    ):
        if fn in handlers:
            handlers.remove(fn)
    _last_camera.clear()
